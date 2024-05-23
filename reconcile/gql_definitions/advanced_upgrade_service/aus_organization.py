"""
Generated by qenerate plugin=pydantic_v1. DO NOT MODIFY MANUALLY!
"""
from collections.abc import Callable  # noqa: F401 # pylint: disable=W0611
from datetime import datetime  # noqa: F401 # pylint: disable=W0611
from enum import Enum  # noqa: F401 # pylint: disable=W0611
from typing import (  # noqa: F401 # pylint: disable=W0611
    Any,
    Optional,
    Union,
)

from pydantic import (  # noqa: F401 # pylint: disable=W0611
    BaseModel,
    Extra,
    Field,
    Json,
)

from reconcile.gql_definitions.fragments.aus_organization import AUSOCMOrganization


DEFINITION = """
fragment AUSOCMOrganization on OpenShiftClusterManager_v1 {
  name
  environment {
    ... OCMEnvironment
  }
  orgId
  accessTokenClientId
  accessTokenUrl
  accessTokenClientSecret {
    ... VaultSecret
  }
  disable {
    ... DisableAutomations
  }
  blockedVersions
  addonManagedUpgrades
  addonUpgradeTests {
    addon {
      name
    }
    instance {
      name
      token {
        ... VaultSecret
      }
    }
    name
  }
  inheritVersionData {
    name
    orgId
    environment {
      name
    }
    publishVersionData {
      ... MinimalOCMOrganization
    }
  }
  publishVersionData {
    ... MinimalOCMOrganization
  }
  sectors {
    name
    dependencies {
      name
      ocm {
        name
      }
    }
  }
  upgradePolicyAllowedWorkloads
  upgradePolicyClusters {
    name
    upgradePolicy {
      ... ClusterUpgradePolicyV1
    }
  }
  ausClusterHealthChecks {
    provider
    enforced
  }
}

fragment ClusterUpgradePolicyV1 on ClusterUpgradePolicy_v1 {
  workloads
  schedule
  versionGateApprovals
  conditions {
    mutexes
    soakDays
    sector
    blockedVersions
  }
}

fragment DisableAutomations on DisableClusterAutomations_v1 {
  integrations
}

fragment MinimalOCMOrganization on OpenShiftClusterManager_v1 {
  name
  orgId
}

fragment OCMEnvironment on OpenShiftClusterManagerEnvironment_v1 {
    name
    description
    labels
    url
    accessTokenClientId
    accessTokenUrl
    accessTokenClientSecret {
        ... VaultSecret
    }
}

fragment VaultSecret on VaultSecret_v1 {
    path
    field
    version
    format
}

query AUSOrganizations($name: String) {
  organizations: ocm_instances_v1(name: $name) {
    ... AUSOCMOrganization
  }
}
"""


class ConfiguredBaseModel(BaseModel):
    class Config:
        smart_union=True
        extra=Extra.forbid


class AUSOrganizationsQueryData(ConfiguredBaseModel):
    organizations: Optional[list[AUSOCMOrganization]] = Field(..., alias="organizations")


def query(query_func: Callable, **kwargs: Any) -> AUSOrganizationsQueryData:
    """
    This is a convenience function which queries and parses the data into
    concrete types. It should be compatible with most GQL clients.
    You do not have to use it to consume the generated data classes.
    Alternatively, you can also mime and alternate the behavior
    of this function in the caller.

    Parameters:
        query_func (Callable): Function which queries your GQL Server
        kwargs: optional arguments that will be passed to the query function

    Returns:
        AUSOrganizationsQueryData: queried data parsed into generated classes
    """
    raw_data: dict[Any, Any] = query_func(DEFINITION, **kwargs)
    return AUSOrganizationsQueryData(**raw_data)
