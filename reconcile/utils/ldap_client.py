from contextlib import contextmanager

from ldap3 import Server, Connection, ALL, SAFE_SYNC
from reconcile.utils.config import get_config

_base_dn = None


@contextmanager
def init(serverUrl):
    server = Server(serverUrl, get_info=ALL)
    client = Connection(server, None, None, client_strategy=SAFE_SYNC)
    try:
        client.bind()
        yield client
    finally:
        client.unbind()


def init_from_config():
    global _base_dn

    config = get_config()

    serverUrl = config['ldap']['server']
    _base_dn = config['ldap']['base_dn']
    return init(serverUrl)


def get_users():
    global _base_dn

    with init_from_config() as client:
        _, _, results, _ = client.search(_base_dn, '(&(objectclass=person))',
                                         attributes=['uid'])
        if results is None:
            return []
        return set(r['attributes']['uid'][0] for r in results)
