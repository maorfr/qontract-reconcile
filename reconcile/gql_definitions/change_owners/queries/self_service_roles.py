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

from reconcile.gql_definitions.fragments.membership_source import RoleMembershipSource


DEFINITION = """
fragment RoleMembershipSource on RoleMembershipSource_V1 {
  group
  provider {
    name
    hasAuditTrail
    source {
      ... on AppInterfaceMembershipProviderSource_V1 {
        url
        username {
          ...VaultSecret
        }
        password {
          ...VaultSecret
        }
      }
    }
  }
}

fragment VaultSecret on VaultSecret_v1 {
    path
    field
    version
    format
}

query SelfServiceRolesQuery($name: String) {
  roles: roles_v1(name: $name) {
    name
    labels
    path
    self_service {
      change_type {
        name
        contextSchema
      }
      datafiles {
        datafileSchema: schema
        path
      }
      resources
    }
    users {
      name
      org_username
      tag_on_merge_requests
    }
    bots {
      name
      org_username
    }
    permissions {
      ... on PermissionSlackUsergroup_v1 {
        handle
        workspace {
          name
        }
        channels
      }
      ... on PermissionGitlabGroupMembership_v1 {
        group
      }
    }
    memberSources {
      ...RoleMembershipSource
    }
  }
}
"""


class ConfiguredBaseModel(BaseModel):
    class Config:
        smart_union=True
        extra=Extra.forbid


class ChangeTypeV1(ConfiguredBaseModel):
    name: str = Field(..., alias="name")
    context_schema: Optional[str] = Field(..., alias="contextSchema")


class DatafileObjectV1(ConfiguredBaseModel):
    datafile_schema: str = Field(..., alias="datafileSchema")
    path: str = Field(..., alias="path")


class SelfServiceConfigV1(ConfiguredBaseModel):
    change_type: ChangeTypeV1 = Field(..., alias="change_type")
    datafiles: Optional[list[DatafileObjectV1]] = Field(..., alias="datafiles")
    resources: Optional[list[str]] = Field(..., alias="resources")


class UserV1(ConfiguredBaseModel):
    name: str = Field(..., alias="name")
    org_username: str = Field(..., alias="org_username")
    tag_on_merge_requests: Optional[bool] = Field(..., alias="tag_on_merge_requests")


class BotV1(ConfiguredBaseModel):
    name: str = Field(..., alias="name")
    org_username: Optional[str] = Field(..., alias="org_username")


class PermissionV1(ConfiguredBaseModel):
    ...


class SlackWorkspaceV1(ConfiguredBaseModel):
    name: str = Field(..., alias="name")


class PermissionSlackUsergroupV1(PermissionV1):
    handle: str = Field(..., alias="handle")
    workspace: SlackWorkspaceV1 = Field(..., alias="workspace")
    channels: list[str] = Field(..., alias="channels")


class PermissionGitlabGroupMembershipV1(PermissionV1):
    group: str = Field(..., alias="group")


class RoleV1(ConfiguredBaseModel):
    name: str = Field(..., alias="name")
    labels: Optional[Json] = Field(..., alias="labels")
    path: str = Field(..., alias="path")
    self_service: Optional[list[SelfServiceConfigV1]] = Field(..., alias="self_service")
    users: list[UserV1] = Field(..., alias="users")
    bots: list[BotV1] = Field(..., alias="bots")
    permissions: Optional[list[Union[PermissionSlackUsergroupV1, PermissionGitlabGroupMembershipV1, PermissionV1]]] = Field(..., alias="permissions")
    member_sources: Optional[list[RoleMembershipSource]] = Field(..., alias="memberSources")


class SelfServiceRolesQueryQueryData(ConfiguredBaseModel):
    roles: Optional[list[RoleV1]] = Field(..., alias="roles")


def query(query_func: Callable, **kwargs: Any) -> SelfServiceRolesQueryQueryData:
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
        SelfServiceRolesQueryQueryData: queried data parsed into generated classes
    """
    raw_data: dict[Any, Any] = query_func(DEFINITION, **kwargs)
    return SelfServiceRolesQueryQueryData(**raw_data)
