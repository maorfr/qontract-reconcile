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


class ConfiguredBaseModel(BaseModel):
    class Config:
        smart_union=True
        extra=Extra.forbid


class User(ConfiguredBaseModel):
    name: str = Field(..., alias="name")
    org_username: str = Field(..., alias="org_username")
    github_username: str = Field(..., alias="github_username")
    slack_username: Optional[str] = Field(..., alias="slack_username")
    pagerduty_username: Optional[str] = Field(..., alias="pagerduty_username")
    tag_on_merge_requests: Optional[bool] = Field(..., alias="tag_on_merge_requests")
