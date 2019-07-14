import os
import shutil
import yaml
import tempfile
import logging
import filecmp
import xml.etree.ElementTree as et
import utils.vault_client as vault_client

import utils.gql as gql

from os import path
from contextlib import contextmanager

from jenkins_jobs.builder import JenkinsManager
from jenkins_jobs.parser import YamlParser
from jenkins_jobs.registry import ModuleRegistry


class FetchResourceError(Exception):
    def __init__(self, msg):
        super(FetchResourceError, self).__init__(
            "error fetching resource: " + str(msg)
        )


class JJB(object):
    """Wrapper around Jenkins Jobs"""

    def __init__(self, configs, ssl_verify=True):
        self.collect_configs(configs)
        self.modify_logger()
        self.python_https_verify = str(int(ssl_verify))

    def collect_configs(self, configs):
        gqlapi = gql.get_api()
        instances = {c['instance']['name']: c['instance']['token']
                     for c in configs}

        working_dirs = {}
        for name, token in instances.items():
            wd = tempfile.mkdtemp()
            ini = vault_client.read(token['path'], token['field'])
            ini = ini.replace('"', '')
            ini = ini.replace('false', 'False')
            ini_file_path = '{}/{}.ini'.format(wd, name)
            with open(ini_file_path, 'w') as f:
                f.write(ini)
                f.write('\n')
            working_dirs[name] = wd

        self.sort(configs)

        for c in configs:
            instance_name = c['instance']['name']
            config = c['config']
            config_file_path = \
                '{}/config.yaml'.format(working_dirs[instance_name])
            if config:
                with open(config_file_path, 'a') as f:
                    yaml.dump(yaml.load(config, Loader=yaml.FullLoader), f)
                    f.write('\n')
            else:
                config_path = c['config_path']
                # get config data
                try:
                    config_resource = gqlapi.get_resource(config_path)
                    config = config_resource['content']
                except gql.GqlApiError as e:
                    raise FetchResourceError(e.message)
                with open(config_file_path, 'a') as f:
                    f.write(config)
                    f.write('\n')

        self.working_dirs = working_dirs

    def sort(self, configs):
        configs.sort(key=self.sort_by_name)
        configs.sort(key=self.sort_by_type)

    def sort_by_type(self, config):
        if config['type'] == 'common':
            return 00
        elif config['type'] == 'views':
            return 10
        elif config['type'] == 'secrets':
            return 20
        elif config['type'] == 'job-templates':
            return 30
        elif config['type'] == 'jobs':
            return 40

    def sort_by_name(self, config):
        return config['name']

    def test(self, io_dir, compare):
        for name, wd in self.working_dirs.items():
            ini_path = '{}/{}.ini'.format(wd, name)
            config_path = '{}/config.yaml'.format(wd)

            fetch_state = 'desired' if compare else 'current'
            output_dir = path.join(io_dir, 'jjb', fetch_state, name)
            args = ['--conf', ini_path,
                    'test', config_path,
                    '-o', output_dir,
                    '--config-xml']
            self.execute(args)
            self.change_files_ownership(io_dir)

        if compare:
            self.print_diffs(io_dir)

    def change_files_ownership(self, io_dir):
        stat_info = os.stat(io_dir)
        uid = stat_info.st_uid
        gid = stat_info.st_gid
        for root, dirs, files in os.walk(io_dir):
            for d in dirs:
                os.chown(path.join(root, d), uid, gid)
            for f in files:
                os.chown(path.join(root, f), uid, gid)

    def print_diffs(self, io_dir):
        current_path = path.join(io_dir, 'jjb', 'current')
        current_files = self.get_files(current_path)
        desired_path = path.join(io_dir, 'jjb', 'desired')
        desired_files = self.get_files(desired_path)

        create = self.compare_files(desired_files, current_files)
        delete = self.compare_files(current_files, desired_files)
        common = self.compare_files(desired_files, current_files, in_op=True)

        self.print_diff(create, desired_path, 'create')
        self.print_diff(delete, current_path, 'delete')
        self.print_diff(common, desired_path, 'update')

    def print_diff(self, files, replace_path, action):
        for f in files:
            if action == 'update':
                ft = self.toggle_cd(f)
                equal = filecmp.cmp(f, ft)
                if equal:
                    continue

            instance, item, _ = f.replace(replace_path + '/', '').split('/')
            item_type = et.parse(f).getroot().tag
            item_type = item_type.replace('hudson.model.ListView', 'view')
            item_type = item_type.replace('project', 'job')
            logging.info([action, item_type, instance, item])

    def compare_files(self, from_files, subtract_files, in_op=False):
        return [f for f in from_files
                if (self.toggle_cd(f) in subtract_files) is in_op]

    def get_files(self, search_path):
        return [path.join(root, f)
                for root, _, files in os.walk(search_path)
                for f in files]

    def toggle_cd(self, file_name):
        if 'desired' in file_name:
            return file_name.replace('desired', 'current')
        else:
            return file_name.replace('current', 'desired')

    def update(self):
        for name, wd in self.working_dirs.items():
            ini_path = '{}/{}.ini'.format(wd, name)
            config_path = '{}/config.yaml'.format(wd)

            args = ['--conf', ini_path, 'update', config_path, '--delete-old']
            self.execute(args)

    def get_jjb(self, args):
        os.environ['PYTHONHTTPSVERIFY'] = self.python_https_verify
        from jenkins_jobs.cli.entry import JenkinsJobs
        return JenkinsJobs(args)

    def execute(self, args):
        jjb = self.get_jjb(args)
        with self.toggle_logger():
            jjb.execute()

    def modify_logger(self):
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        logger = logging.getLogger()
        logger.handlers[0].setFormatter(formatter)
        self.default_logging = logger.level

    @contextmanager
    def toggle_logger(self):
        logger = logging.getLogger()
        try:
            yield logger.setLevel(logging.ERROR)
        finally:
            logger.setLevel(self.default_logging)

    def cleanup(self):
        for wd in self.working_dirs.values():
            shutil.rmtree(wd)

    def get_job_webhooks_data(self):
        job_webhooks_data = []
        for name, wd in self.working_dirs.items():
            ini_path = '{}/{}.ini'.format(wd, name)
            config_path = '{}/config.yaml'.format(wd)

            args = ['--conf', ini_path, 'test', config_path]
            jjb = self.get_jjb(args)
            builder = JenkinsManager(jjb.jjb_config)
            registry = ModuleRegistry(jjb.jjb_config, builder.plugins_list)
            parser = YamlParser(jjb.jjb_config)
            parser.load_files(jjb.options.path)

            jobs, _ = parser.expandYaml(
                registry, jjb.options.names)

            for job in jobs:
                try:
                    project_url_raw = job['properties'][0]['github']['url']
                    if 'https://github.com' in project_url_raw:
                        continue
                    project_url = project_url_raw.strip('/').replace('.git', '')
                    gitlab_triggers = job['triggers'][0]['gitlab']
                    mr_trigger = gitlab_triggers['trigger-merge-request']
                    trigger = 'pr-check' if mr_trigger else 'build-master'
                    item = {
                        'job_name': job['name'],
                        'repo_url': project_url,
                        'trigger': trigger,
                    }
                    job_webhooks_data.append(item)
                except KeyError:
                    continue
        return job_webhooks_data
