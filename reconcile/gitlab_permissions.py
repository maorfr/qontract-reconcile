import logging

import utils.threaded as threaded
import reconcile.queries as queries

from utils.gitlab_api import GitLabApi


def get_members_to_add(repo, gl, app_sre):
    maintainers = gl.get_project_maintainers(repo)
    if gl.user.username not in maintainers:
        logging.error("'{}' is not shared with {} as 'Maintainer'".format(
            repo, gl.user.username
        ))
        return []
    members_to_add = [{
        "user": u, "repo": repo} for u in app_sre
        if u.username not in maintainers]
    return members_to_add


def run(dry_run=False, thread_pool_size=10):
    instance = queries.get_gitlab_instance()
    gl = GitLabApi(instance)
    repos = queries.get_repos(server=gl.server)
    app_sre = gl.get_app_sre_group_users()
    results = threaded.run(get_members_to_add, repos, thread_pool_size,
                           gl=gl, app_sre=app_sre)

    members_to_add = [item for sublist in results for item in sublist]
    for m in members_to_add:
        logging.info(['add_maintainer', m["repo"], m["user"].username])
        if not dry_run:
            gl.add_project_member(m["repo"], m["user"])
