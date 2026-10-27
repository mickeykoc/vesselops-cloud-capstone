"""SDK-adapter contract tests with fakes; these are not live Cosmos tests."""

from unittest.mock import MagicMock, patch
import pytest
from azure.core import MatchConditions
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceExistsError, CosmosResourceNotFoundError
from app.store import Conflict, CosmosStore, Missing


@pytest.fixture
def store():
    with patch("azure.cosmos.CosmosClient"):
        instance = CosmosStore("https://test.documents.azure.com", MagicMock())
    return instance


def test_create_removes_local_version_and_maps_etag(store):
    store.container.create_item.return_value = {"id": "1", "kind": "ticket", "_etag": "etag1", "_rid": "internal"}
    assert store.create({"id": "1", "kind": "ticket", "version": "stale"}) == {
        "id": "1",
        "kind": "ticket",
        "version": "etag1",
    }
    assert "version" not in store.container.create_item.call_args.kwargs["body"]


def test_replace_uses_etag_precondition(store):
    store.container.replace_item.return_value = {"id": "1", "kind": "ticket", "_etag": "new"}
    store.replace({"id": "1", "kind": "ticket", "version": "old"}, "old")
    kwargs = store.container.replace_item.call_args.kwargs
    assert kwargs["etag"] == "old"
    assert kwargs["match_condition"] == MatchConditions.IfNotModified


def test_conflicts_and_missing_are_mapped(store):
    store.container.replace_item.side_effect = CosmosHttpResponseError(status_code=412, message="stale")
    with pytest.raises(Conflict):
        store.replace({"id": "1", "kind": "ticket"}, "old")
    store.container.read_item.side_effect = CosmosResourceNotFoundError(status_code=404, message="missing")
    with pytest.raises(Missing):
        store.get("ticket", "1")
    store.container.create_item.side_effect = CosmosResourceExistsError(status_code=409, message="duplicate")
    with pytest.raises(Conflict):
        store.create({"id": "1", "kind": "ticket"})


def test_list_is_partition_scoped(store):
    store.container.query_items.return_value = [{"id": "1", "kind": "asset", "_etag": "a"}]
    assert store.list("asset")[0]["version"] == "a"
    assert store.container.query_items.call_args.kwargs["partition_key"] == "asset"


def test_other_cosmos_failure_not_masked(store):
    store.container.replace_item.side_effect = CosmosHttpResponseError(status_code=403, message="denied")
    with pytest.raises(CosmosHttpResponseError):
        store.replace({"id": "1", "kind": "ticket"}, "old")
