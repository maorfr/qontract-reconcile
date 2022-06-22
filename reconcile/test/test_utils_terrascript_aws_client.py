import pytest

import reconcile.utils.terrascript_aws_client as tsclient
from reconcile.utils.external_resource_spec import (
    ExternalResourceSpec,
    ExternalResourceUniqueKey,
)


def test_sanitize_resource_with_dots():
    assert tsclient.safe_resource_id("foo.example.com") == "foo_example_com"


def test_sanitize_resource_with_wildcard():
    assert tsclient.safe_resource_id("*.foo.example.com") == "_star_foo_example_com"


@pytest.fixture
def ts():
    return tsclient.TerrascriptClient("", "", 1, [])


def test_aws_username_org(ts):
    result = "org"
    user = {"org_username": result}
    assert ts._get_aws_username(user) == result


def test_aws_username_aws(ts):
    result = "aws"
    user = {"org_username": "org", "aws_username": result}
    assert ts._get_aws_username(user) == result


def test_validate_mandatory_policies(ts):
    mandatory_policy = {
        "name": "mandatory",
        "mandatory": True,
    }
    not_mandatory_policy = {
        "name": "not-mandatory",
    }
    account = {"name": "acc", "policies": [mandatory_policy, not_mandatory_policy]}
    assert ts._validate_mandatory_policies(account, [mandatory_policy], "role") is True
    assert (
        ts._validate_mandatory_policies(account, [not_mandatory_policy], "role")
        is False
    )


class MockJenkinsApi:
    def __init__(self, response):
        self.response = response

    def is_job_running(self, name):
        return self.response


def test_use_previous_image_id_no_upstream(ts):
    assert ts._use_previous_image_id({}) is False


def test_use_previous_image_id_false(mocker, ts):
    result = False
    mocker.patch(
        "reconcile.utils.terrascript_aws_client.TerrascriptClient.init_jenkins",
        return_value=MockJenkinsApi(result),
    )
    image = {"upstream": {"instance": {"name": "ci"}, "name": "job"}}
    assert ts._use_previous_image_id(image) == result


def test_use_previous_image_id_true(mocker, ts):
    result = True
    mocker.patch(
        "reconcile.utils.terrascript_aws_client.TerrascriptClient.init_jenkins",
        return_value=MockJenkinsApi(result),
    )
    image = {"upstream": {"instance": {"name": "ci"}, "name": "job"}}
    assert ts._use_previous_image_id(image) == result


def test_tf_disabled_namespace_with_resources(ts):
    """
    even if a namespace has tf resources, they are not considered when the
    namespace is not enabled for tf resource management
    """
    ra = {"identifier": "a", "provider": "p"}
    ns1 = {
        "name": "ns1",
        "managedExternalResources": False,
        "externalResources": [
            {"provider": "aws", "provisioner": {"name": "a"}, "resources": [ra]}
        ],
        "cluster": {"name": "c"},
    }
    namespaces = [ns1]
    ts.init_populate_specs(namespaces, None)
    specs = ts.resource_spec_inventory
    assert not specs


def test_resource_specs_without_account_filter(ts):
    """
    if no account filter is given, all resources of namespaces with
    enabled tf resource management are expected to be returned
    """
    p = "aws"
    pa = {"name": "a"}
    ra = {"identifier": "a", "provider": "p"}
    ns1 = {
        "name": "ns1",
        "managedExternalResources": True,
        "externalResources": [{"provider": p, "provisioner": pa, "resources": [ra]}],
        "cluster": {"name": "c"},
    }
    namespaces = [ns1]
    ts.init_populate_specs(namespaces, None)
    specs = ts.resource_spec_inventory
    spec = ExternalResourceSpec(p, pa, ra, ns1)
    assert specs == {ExternalResourceUniqueKey.from_spec(spec): spec}


def test_resource_specs_with_account_filter(ts):
    """
    if an account filter is given only the resources defined for
    that account are expected
    """
    p = "aws"
    pa = {"name": "a"}
    ra = {"identifier": "a", "provider": "p"}
    pb = {"name": "b"}
    rb = {"identifier": "b", "provider": "p"}
    ns1 = {
        "name": "ns1",
        "managedExternalResources": True,
        "externalResources": [
            {"provider": p, "provisioner": pa, "resources": [ra]},
            {"provider": p, "provisioner": pb, "resources": [rb]},
        ],
        "cluster": {"name": "c"},
    }
    namespaces = [ns1]
    ts.init_populate_specs(namespaces, "a")
    specs = ts.resource_spec_inventory
    spec = ExternalResourceSpec(p, pa, ra, ns1)
    assert specs == {ExternalResourceUniqueKey.from_spec(spec): spec}
