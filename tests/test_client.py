"""Facade tests: the boundary under test is the ``Gateway.unary`` seam the
facade routes through — that it sends the right procedure, maps the ergonomic
arguments onto the right protobuf fields, and unwraps the response. Transport
and auth are the runtime's concern, so the gateway here is a capturing fake."""

from __future__ import annotations

import datasource
from saas.accounts.v1 import datasource_pb2 as pb


class RecordingGateway:
    """Captures each call and returns a canned response of the requested type."""

    def __init__(self, responses: dict[str, object] | None = None) -> None:
        self.calls: list[tuple[str, object]] = []
        self._responses = responses or {}

    def unary(self, procedure, request, response_type):
        self.calls.append((procedure, request))
        canned = self._responses.get(procedure)
        return canned if canned is not None else response_type()


def test_add_github_source_maps_fields_and_unwraps():
    gw = RecordingGateway(
        {
            "/saas.accounts.v1.DatasourceService/AddGitHubSource": pb.AddGitHubSourceResponse(
                datasource=pb.Datasource(id="ds-1", target_collection="handbook")
            )
        }
    )
    ds = datasource.new(gw)

    source = ds.add_github_source(
        org_id="11111111-1111-1111-1111-111111111111",
        repo="codefly-dev/module-saas-starter",
        paths=["docs", "handbook"],
        branch="main",
        collection="handbook",
        access_token="ghp_secret",
        webhook_secret="whsec",
    )

    procedure, request = gw.calls[0]
    assert procedure == "/saas.accounts.v1.DatasourceService/AddGitHubSource"
    # Ergonomic kwargs land on the right proto fields.
    assert request.repo == "codefly-dev/module-saas-starter"
    assert request.target_collection == "handbook"
    assert request.access_token == "ghp_secret"
    assert request.webhook_secret == "whsec"
    assert list(request.paths) == ["docs", "handbook"]
    assert request.branch == "main"
    # The response envelope is unwrapped to the bare Datasource.
    assert source.id == "ds-1"
    assert source.target_collection == "handbook"


def test_list_sources_returns_bare_list():
    gw = RecordingGateway(
        {
            "/saas.accounts.v1.DatasourceService/ListSources": pb.ListSourcesResponse(
                datasources=[pb.Datasource(id="a"), pb.Datasource(id="b")]
            )
        }
    )

    sources = datasource.new(gw).list_sources("org-1")

    procedure, request = gw.calls[0]
    assert procedure == "/saas.accounts.v1.DatasourceService/ListSources"
    assert request.org_id == "org-1"
    assert [s.id for s in sources] == ["a", "b"]


def test_get_source_passes_ids():
    gw = RecordingGateway(
        {
            "/saas.accounts.v1.DatasourceService/GetSource": pb.GetSourceResponse(
                datasource=pb.Datasource(id="ds-9")
            )
        }
    )

    source = datasource.new(gw).get_source("org-1", "ds-9")

    _, request = gw.calls[0]
    assert request.org_id == "org-1" and request.id == "ds-9"
    assert source.id == "ds-9"


def test_sync_source_returns_job_id():
    gw = RecordingGateway(
        {
            "/saas.accounts.v1.DatasourceService/SyncSource": pb.SyncSourceResponse(job_id="job-42")
        }
    )

    job_id = datasource.new(gw).sync_source("org-1", "ds-1")

    procedure, request = gw.calls[0]
    assert procedure == "/saas.accounts.v1.DatasourceService/SyncSource"
    assert request.org_id == "org-1" and request.id == "ds-1"
    assert job_id == "job-42"


def test_delete_source_passes_ids():
    gw = RecordingGateway()

    result = datasource.new(gw).delete_source("org-1", "ds-1")

    procedure, request = gw.calls[0]
    assert procedure == "/saas.accounts.v1.DatasourceService/DeleteSource"
    assert request.org_id == "org-1" and request.id == "ds-1"
    assert result is None
