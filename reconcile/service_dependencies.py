import sys
import logging

import utils.gql as gql
import reconcile.queries as queries


APPS_QUERY = """
{
  apps: apps_v1 {
    name
    dependencies {
      name
    }
    codeComponents {
      url
    }
    quayRepos {
      org {
        name
      }
    }
    namespaces {
      managedTerraformResources
    }
  }
}
"""

QONTRACT_INTEGRATION = 'service-dependencies'


def get_dependency_names(dependency_map, dep_type):
    dep_names = []
    for dm in dependency_map:
        if dm['type'] != dep_type:
            continue
        for service in dm['services']:
            dep_names.append(service['name'])
    return dep_names


def get_desired_dependency_names(app, dependency_map):
    required_dep_names = set()

    code_components = app.get('codeComponents')
    if code_components:
        gitlab_urls = [cc for cc in code_components
                       if 'gitlab' in cc['url']]
        if gitlab_urls:
            required_dep_names.update(
                get_dependency_names(dependency_map, 'gitlab'))
        github_urls = [cc for cc in code_components
                       if 'github.com' in cc['url']]
        if github_urls:
            required_dep_names.update(
                get_dependency_names(dependency_map, 'github'))

    quay_repos = app.get('quayRepos')
    if quay_repos:
        required_dep_names.update(
            get_dependency_names(dependency_map, 'quay'))

    namespaces = app.get('namespaces')
    if namespaces:
        required_dep_names.update(
            get_dependency_names(dependency_map, 'openshift'))
        tf_namespaces = [n for n in namespaces
                         if n.get('managedTerraformResources')]
        if tf_namespaces:
            required_dep_names.update(
                get_dependency_names(dependency_map, 'aws'))

    return required_dep_names


def run(dry_run):
    settings = queries.get_app_interface_settings()
    dependency_map = settings.get('dependencies')
    if not dependency_map:
        sys.exit()

    gqlapi = gql.get_api()
    apps = gqlapi.query(APPS_QUERY)['apps']
    error = False
    for app in apps:
        app_name = app['name']
        app_deps = app.get('dependencies')
        current_deps = \
            [a['name'] for a in app_deps] if app_deps else []
        desired_deps = get_desired_dependency_names(app, dependency_map)

        missing_deps = list(desired_deps.difference(current_deps))
        if missing_deps:
            error = True
            msg = f"App '{app_name}' has missing dependencies: {missing_deps}"
            logging.error(msg)

    if error:
        sys.exit(1)
