import sys
import shutil

import reconcile.queries as queries

from utils.defer import defer
from utils.aws_api import AWSApi
from utils.terrascript_client import TerrascriptClient as Terrascript


def get_keys_to_delete(accounts):
    return {account['name']: account['deleteKeys']
            for account in accounts
            if account['deleteKeys'] not in (None, [])}


def init_tf_working_dirs(accounts, thread_pool_size):
    # copied here to avoid circular dependency
    QONTRACT_INTEGRATION = 'terraform_resources'
    QONTRACT_TF_PREFIX = 'qrtf'
    ts = Terrascript(QONTRACT_INTEGRATION,
                     QONTRACT_TF_PREFIX,
                     thread_pool_size,
                     accounts)
    working_dirs, _ = ts.dump()
    # no use for terrascript for us here
    # and an error here is very unlikely
    return working_dirs


def cleanup(working_dirs):
    for wd in working_dirs.values():
        shutil.rmtree(wd)


@defer
def run(dry_run=False, thread_pool_size=10,
        disable_service_account_keys=False, defer=None):
    accounts = queries.get_aws_accounts()
    aws = AWSApi(thread_pool_size, accounts)
    keys_to_delete = get_keys_to_delete(accounts)
    working_dirs = init_tf_working_dirs(accounts, thread_pool_size)
    defer(lambda: cleanup(working_dirs))
    error = aws.delete_keys(dry_run, keys_to_delete, working_dirs,
                            disable_service_account_keys)
    if error:
        sys.exit(1)
