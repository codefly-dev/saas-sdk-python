"""End-to-end facade tests over a real Connect-unary HTTP round-trip.

The boundary under test is the wire contract: that the facade posts to the
*actual* ``/saas.accounts.v1.DatasourceService/<Method>`` procedure the server
exposes, serializes the right request, and unwraps the response. A fake in-proc
gateway can't catch a wrong procedure string (it would echo whatever the SUT
sent), so the test stands up a real HTTP server and drives it through a real
``Gateway`` that speaks Connect-unary proto exactly as ``solution_runtime`` does.
"""

from __future__ import annotations

import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from saas_sdk import datasource
from saas_sdk._gen import datasource_pb2 as pb


class Gateway:
    """Real Connect-unary gateway: the minimal transport the runtime provides,
    reproduced here so the test exercises actual HTTP, not a stub."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def unary(self, procedure, request, response_type):
        http_request = urllib.request.Request(
            f"{self.base_url}{procedure}",
            data=request.SerializeToString(),
            headers={
                "content-type": "application/proto",
                "connect-protocol-version": "1",
            },
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=10) as http_response:
            body = http_response.read()
        message = response_type()
        message.ParseFromString(body)
        return message


# Wire handlers keyed by the exact procedure path the real service exposes. If
# the facade posts to any other path, the server 404s and the call fails.
_ROUTES = {
    "/saas.accounts.v1.DatasourceService/AddGitHubSource": (
        pb.AddGitHubSourceRequest,
        lambda req: pb.AddGitHubSourceResponse(
            datasource=pb.Datasource(id="ds-1", target_collection=req.target_collection)
        ),
    ),
    "/saas.accounts.v1.DatasourceService/ListSources": (
        pb.ListSourcesRequest,
        lambda req: pb.ListSourcesResponse(
            datasources=[pb.Datasource(id="a"), pb.Datasource(id="b")]
        ),
    ),
    "/saas.accounts.v1.DatasourceService/SyncSource": (
        pb.SyncSourceRequest,
        lambda req: pb.SyncSourceResponse(job_id="job-42"),
    ),
}


@pytest.fixture
def server():
    received: list[tuple[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence test output
            pass

        def do_POST(self):
            route = _ROUTES.get(self.path)
            if route is None:
                self.send_error(404)
                return
            request_type, respond = route
            body = self.rfile.read(int(self.headers["Content-Length"]))
            request = request_type.FromString(body)
            received.append((self.path, request))
            payload = respond(request).SerializeToString()
            self.send_response(200)
            self.send_header("content-type", "application/proto")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    client = datasource.new(Gateway(f"http://{host}:{port}"))
    try:
        yield client, received
    finally:
        httpd.shutdown()


def test_add_github_source_maps_fields_and_unwraps(server):
    client, received = server

    source = client.add_github_source(
        org_id="11111111-1111-1111-1111-111111111111",
        repo="codefly-dev/module-saas-starter",
        paths=["docs", "handbook"],
        branch="main",
        collection="handbook",
        access_token="ghp_secret",
        webhook_secret="whsec",
    )

    path, request = received[0]
    assert path == "/saas.accounts.v1.DatasourceService/AddGitHubSource"
    assert request.repo == "codefly-dev/module-saas-starter"
    assert request.target_collection == "handbook"
    assert request.access_token == "ghp_secret"
    assert request.webhook_secret == "whsec"
    assert list(request.paths) == ["docs", "handbook"]
    assert request.branch == "main"
    # Response envelope unwrapped to the bare Datasource.
    assert source.id == "ds-1"
    assert source.target_collection == "handbook"


def test_list_sources_returns_bare_list(server):
    client, received = server

    sources = client.list_sources("org-1")

    path, request = received[0]
    assert path == "/saas.accounts.v1.DatasourceService/ListSources"
    assert request.org_id == "org-1"
    assert [s.id for s in sources] == ["a", "b"]


def test_sync_returns_job_id(server):
    client, received = server

    job_id = client.sync("org-1", "ds-1")

    path, request = received[0]
    assert path == "/saas.accounts.v1.DatasourceService/SyncSource"
    assert request.org_id == "org-1" and request.id == "ds-1"
    assert job_id == "job-42"
