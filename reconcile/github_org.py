import logging
from github import Github
from github.GithubObject import NotSet

import utils.gql as gql
import utils.vault_client as vault_client

from utils.aggregated_list import AggregatedList, AggregatedDiffRunner
from utils.raw_github_api import RawGithubApi
from utils.retry import retry

ORGS_QUERY = """
{
  orgs: githuborg_v1 {
    name
    token {
      path
      field
      version
    }
    managedTeams
  }
}
"""

QUERY = """
{
  roles: roles_v1 {
    name
    users {
      github_username
    }
    bots {
      github_username
    }
    permissions {
      service
      ...on PermissionGithubOrg_v1 {
        org
      }
      ...on PermissionGithubOrgTeam_v1 {
        org
        team
      }
    }
  }
}
"""


def get_config():
    gqlapi = gql.get_api()
    orgs = gqlapi.query(ORGS_QUERY)['orgs']

    config = {'github': {}}
    for org in orgs:
        org_name = org['name']
        token = vault_client.read(org['token'])
        org_config = {'token': token, 'managed_teams': org['managedTeams']}
        config['github'][org_name] = org_config

    return config


@retry()
def fetch_current_state(gh_api_store):
    state = AggregatedList()

    for org_name in gh_api_store.orgs():
        g = gh_api_store.github(org_name)
        raw_gh_api = gh_api_store.raw_github_api(org_name)
        managed_teams = gh_api_store.managed_teams(org_name)
        # if 'managedTeams' is not specified
        # we manage all teams
        is_managed = managed_teams is None or len(managed_teams) == 0

        org = g.get_organization(org_name)

        org_members = None
        if is_managed:
            org_members = [member.login for member in org.get_members()]
            org_members.extend(raw_gh_api.org_invitations(org_name))
            org_members = [m.lower() for m in org_members]

        all_team_members = []
        for team in org.get_teams():
            if not is_managed and team.name not in managed_teams:
                continue

            members = [member.login for member in team.get_members()]
            members.extend(raw_gh_api.team_invitations(team.id))
            members = [m.lower() for m in members]
            all_team_members.extend(members)

            state.add(
                {
                    'service': 'github-org-team',
                    'org': org_name,
                    'team': team.name
                },
                members
            )
        all_team_members = list(set(all_team_members))

        members = org_members or all_team_members
        state.add(
            {
                'service': 'github-org',
                'org': org_name,
            },
            members
        )

    return state


def fetch_desired_state():
    gqlapi = gql.get_api()
    result = gqlapi.query(QUERY)

    state = AggregatedList()

    for role in result['roles']:
        permissions = list(filter(
            lambda p: p.get('service') in ['github-org', 'github-org-team'],
            role['permissions']
        ))

        if permissions:
            members = []

            for user in role['users']:
                members.append(user['github_username'])

            for bot in role['bots']:
                if 'github_username' in bot:
                    members.append(bot['github_username'])
            members = [m.lower() for m in members]

            for permission in permissions:
                if permission['service'] == 'github-org':
                    state.add(permission, members)
                elif permission['service'] == 'github-org-team':
                    state.add(permission, members)
                    state.add({
                        'service': 'github-org',
                        'org': permission['org'],
                    }, members)

    return state


class GHApiStore(object):
    _orgs = {}

    def __init__(self, config):
        for org_name, org_config in config['github'].items():
            token = org_config['token']
            managed_teams = org_config.get('managed_teams', None)
            self._orgs[org_name] = \
                (Github(token), RawGithubApi(token), managed_teams)

    def orgs(self):
        return self._orgs.keys()

    def github(self, org_name):
        return self._orgs[org_name][0]

    def raw_github_api(self, org_name):
        return self._orgs[org_name][1]

    def managed_teams(self, org_name):
        return self._orgs[org_name][2]


class RunnerAction(object):
    def __init__(self, dry_run, gh_api_store):
        self.dry_run = dry_run
        self.gh_api_store = gh_api_store

    def add_to_team(self):
        label = "add_to_team"

        def action(params, items):
            org = params["org"]
            team = params["team"]

            if self.dry_run:
                for member in items:
                    logging.info([label, member, org, team])
            else:
                g = self.gh_api_store.github(org)
                gh_org = g.get_organization(org)
                teams = {team.name: team.id for team in gh_org.get_teams()}
                gh_team = gh_org.get_team(teams[team])

                for member in items:
                    logging.info([label, member, org, team])
                    gh_user = g.get_user(member)
                    gh_team.add_membership(gh_user, "member")

        return action

    def del_from_team(self):
        label = "del_from_team"

        def action(params, items):
            org = params["org"]
            team = params["team"]

            if self.dry_run:
                for member in items:
                    logging.info([label, member, org, team])
            else:
                g = self.gh_api_store.github(org)
                gh_org = g.get_organization(org)
                teams = {team.name: team.id for team in gh_org.get_teams()}
                gh_team = gh_org.get_team(teams[team])

                for member in items:
                    logging.info([label, member, org, team])
                    gh_user = g.get_user(member)
                    gh_team.remove_membership(gh_user)

                members = gh_team.get_members()
                if len(list(members)) == 0:
                    logging.info(["del_team", org, team])
                    gh_team.delete()

        return action

    def create_team(self):
        label = "create_team"

        def action(params, items):
            org = params["org"]
            team = params["team"]

            logging.info([label, org, team])

            if not self.dry_run:
                g = self.gh_api_store.github(org)
                gh_org = g.get_organization(org)

                repo_names = NotSet
                permission = NotSet
                privacy = "secret"

                gh_org.create_team(team, repo_names, permission, privacy)

        return action

    def add_to_org(self):
        label = "add_to_org"

        def action(params, items):
            org = params["org"]

            if self.dry_run:
                for member in items:
                    logging.info([label, member, org])
            else:
                g = self.gh_api_store.github(org)
                gh_org = g.get_organization(org)

                for member in items:
                    logging.info([label, member, org])
                    gh_user = g.get_user(member)
                    gh_org.add_to_members(gh_user, 'member')

        return action

    def del_from_org(self):
        label = "del_from_org"

        def action(params, items):
            org = params["org"]

            if self.dry_run:
                for member in items:
                    logging.info([label, member, org])
            else:
                g = self.gh_api_store.github(org)
                gh_org = g.get_organization(org)

                for member in items:
                    logging.info([label, member, org])

                    if not self.dry_run:
                        gh_user = g.get_user(member)
                        gh_org.remove_from_membership(gh_user)

        return action

    @staticmethod
    def raise_exception(msg):
        def raiseException(params, items):
            raise Exception(msg)
        return raiseException


def service_is(service):
    return lambda params: params.get("service") == service


def run(dry_run=False):
    config = get_config()
    gh_api_store = GHApiStore(config)

    current_state = fetch_current_state(gh_api_store)
    desired_state = fetch_desired_state()

    # Ensure current_state and desired_state match orgs
    current_orgs = set([
        item["params"]["org"]
        for item in current_state.dump()
    ])

    desired_orgs = set([
        item["params"]["org"]
        for item in desired_state.dump()
    ])

    assert current_orgs == desired_orgs, \
        "Current orgs ({}) don't match desired orgs ({})".format(
            current_orgs,
            desired_orgs
        )

    # Calculate diff
    diff = current_state.diff(desired_state)

    # Run actions
    runner_action = RunnerAction(dry_run, gh_api_store)
    runner = AggregatedDiffRunner(diff)

    # insert github-org
    runner.register(
        "insert",
        runner_action.raise_exception("Cannot create a Github Org"),
        service_is("github-org"),
    )

    # insert github-org-team
    runner.register(
        "insert",
        runner_action.create_team(),
        service_is("github-org-team"),
    )
    runner.register(
        "insert",
        runner_action.add_to_team(),
        service_is("github-org-team"),
    )

    # delete github-org
    runner.register(
        "delete",
        runner_action.raise_exception("Cannot delete a Github Org"),
        service_is("github-org"),
    )

    # delete github-org-team
    runner.register(
        "delete",
        runner_action.del_from_team(),
        service_is("github-org-team"),
    )

    # update-insert github-org
    runner.register(
        "update-insert",
        runner_action.add_to_org(),
        service_is("github-org"),
    )

    # update-insert github-org-team
    runner.register(
        "update-insert",
        runner_action.add_to_team(),
        service_is("github-org-team"),
    )

    # update-delete github-org
    runner.register(
        "update-delete",
        runner_action.del_from_org(),
        service_is("github-org"),
    )

    # update-delete github-org-team
    runner.register(
        "update-delete",
        runner_action.del_from_team(),
        service_is("github-org-team"),
    )

    runner.run()
