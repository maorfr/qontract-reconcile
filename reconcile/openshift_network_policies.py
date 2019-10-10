import logging
import semver

import utils.gql as gql
import reconcile.openshift_base as ob

from utils.openshift_resource import OR
from utils.defer import defer


NAMESPACES_QUERY = """
{
  namespaces: namespaces_v1 {
    name
    cluster {
      name
      serverUrl
      jumpHost {
          hostname
          knownHosts
          user
          port
          identity {
              path
              field
              format
          }
      }
      automationToken {
        path
        field
        format
      }
      disable {
        integrations
      }
    }
    networkPoliciesAllow {
        name
        cluster {
            name
        }
    }
  }
}
"""

QONTRACT_INTEGRATION = 'openshift-network-policies'
QONTRACT_INTEGRATION_VERSION = semver.format_version(0, 1, 0)


def construct_oc_resource(name, source_ns):
    body = {
        "apiVersion": "extensions/v1beta1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": name
        },
        "spec": {
            "ingress": [{
                "from": [{
                   "namespaceSelector": {
                       "matchLabels": {
                           "name": source_ns
                       }
                   }
                }]
            }],
            "podSelector": {},
            "policyTypes": [
                "Ingress"
            ]
        }
    }
    return OR(body, QONTRACT_INTEGRATION, QONTRACT_INTEGRATION_VERSION)


def fetch_desired_state(namespaces, ri):
    for namespace_info in namespaces:
        namespace = namespace_info['name']
        cluster = namespace_info['cluster']['name']
        source_namespaces = namespace_info['networkPoliciesAllow']
        for source_namespace_info in source_namespaces:
            source_namespace = source_namespace_info['name']
            source_cluster = source_namespace_info['cluster']['name']
            if cluster != source_cluster:
                msg = (
                    "[{}/{}] Network Policy from cluster '{}' not allowed."
                ).format(cluster, namespace, source_cluster)
                logging.error(msg)
                continue
            resource_name = "allow-from-{}-namespace".format(source_namespace)
            oc_resource = \
                construct_oc_resource(resource_name, source_namespace)
            ri.add_desired(
                cluster,
                namespace,
                'NetworkPolicy',
                resource_name,
                oc_resource
            )


@defer
def run(dry_run=False, thread_pool_size=10, defer=None):
    gqlapi = gql.get_api()
    namespaces = [namespace_info for namespace_info
                  in gqlapi.query(NAMESPACES_QUERY)['namespaces']
                  if namespace_info.get('networkPoliciesAllow')]
    ri, oc_map = \
        ob.fetch_current_state(namespaces, thread_pool_size,
                               QONTRACT_INTEGRATION,
                               QONTRACT_INTEGRATION_VERSION,
                               override_managed_types=['NetworkPolicy'])
    defer(lambda: oc_map.cleanup())
    fetch_desired_state(namespaces, ri)
    ob.realize_data(dry_run, oc_map, ri)
