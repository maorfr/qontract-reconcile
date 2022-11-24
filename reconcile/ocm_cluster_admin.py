import sys
import logging
from typing import Any, Mapping

from reconcile import queries
from reconcile.status import ExitCodes
from reconcile.utils.ocm import OCMMap
from reconcile.ocm.utils import cluster_disabled_integrations

QONTRACT_INTEGRATION = "ocm-cluster-admin"


def _cluster_is_compatible(cluster: Mapping[str, Any]) -> bool:
    return (
        cluster.get("ocm") is not None
        and cluster.get("clusterAdminAutomationToken") is not None
    )


def run(dry_run, thread_pool_size=10):
    settings = queries.get_app_interface_settings()
    clusters = queries.get_clusters()
    clusters = [
        c
        for c in clusters
        if QONTRACT_INTEGRATION not in cluster_disabled_integrations(c)
        and _cluster_is_compatible(c)
    ]

    if not clusters:
        logging.debug("No cluster admin definitions found in app-interface")
        sys.exit(ExitCodes.SUCCESS)

    ocm_map = OCMMap(
        clusters=clusters, integration=QONTRACT_INTEGRATION, settings=settings
    )
    for cluster in clusters:
        cluster_name = cluster["name"]
        ocm = ocm_map.get(cluster_name)
        if not ocm.is_cluster_admin_enabled(cluster_name):
            logging.info(["enable_cluster_admin", cluster_name])
            if not dry_run:
                ocm.enable_cluster_admin(cluster_name)
