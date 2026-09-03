"""End-to-end mint-client tests over a real Connect-unary HTTP round-trip.

Same boundary as the datasource facade tests: a real HTTP server keyed by the
*actual* ``/saas.accounts.v1.WorkContextService/<Method>`` procedures, so a
wrong procedure string 404s instead of being echoed back by a stub. The gateway
here also forwards the caller's bearer as ``Authorization``, which is what makes
these mint calls owner-bound, so the server captures it for assertion.
"""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from saas_sdk import work_context
from saas_sdk._gen import work_contexts_pb2 as pb


class Gateway:
    """Real Connect-unary gateway presenting the per-call bearer as the
    request's Authorization, reproduced so the test exercises actual HTTP."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def unary(self, procedure, request, response_type, *, bearer):
        http_request = urllib.request.Request(
            f"{self.base_url}{procedure}",
            data=request.SerializeToString(),
            headers={
                "content-type": "application/proto",
                "connect-protocol-version": "1",
                "authorization": f"Bearer {bearer}",
            },
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=10) as http_response:
            body = http_response.read()
        message = response_type()
        message.ParseFromString(body)
        return message


def _issued(req):
    return pb.IssuedWorkContext(token="head.sig", org_id=req.org_id, task_id="task-1")


_ROUTES = {
    "/saas.accounts.v1.WorkContextService/StartTask": (
        pb.StartTaskWorkContextRequest,
        _issued,
    ),
    "/saas.accounts.v1.WorkContextService/ExchangeAudience": (
        pb.ExchangeWorkContextAudienceRequest,
        _issued,
    ),
    "/saas.accounts.v1.WorkContextService/RenewWorkContext": (
        pb.RenewWorkContextRequest,
        _issued,
    ),
}


@pytest.fixture
def server():
    received: list[tuple[str, object, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            route = _ROUTES.get(self.path)
            if route is None:
                self.send_error(404)
                return
            request_type, respond = route
            body = self.rfile.read(int(self.headers["Content-Length"]))
            request = request_type.FromString(body)
            received.append((self.path, request, self.headers.get("authorization")))
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
    client = work_context.new(Gateway(f"http://{host}:{port}"))
    try:
        yield client, received
    finally:
        httpd.shutdown()


ORG = "11111111-1111-1111-1111-111111111111"
TASK = "22222222-2222-2222-2222-222222222222"
SESSION = "33333333-3333-3333-3333-333333333333"
SCOPE = pb.WorkContextScope(resource_kind="evidence", actions=["read"])


def test_start_task_maps_fields_presents_bearer_and_defaults_ttl(server):
    client, received = server

    issued = client.start_task(
        bearer="user-token",
        org_id=ORG,
        task_id=TASK,
        session_id=SESSION,
        audience="accounts",
        scopes=[SCOPE],
        actor_principal_id="agent-1",
    )

    path, request, authorization = received[0]
    assert path == "/saas.accounts.v1.WorkContextService/StartTask"
    assert authorization == "Bearer user-token"
    assert request.org_id == ORG
    assert request.task_id == TASK
    assert request.session_id == SESSION
    assert request.audience == "accounts"
    assert request.actor_principal_id == "agent-1"
    assert list(request.authority_scopes) == [SCOPE]
    # Unset TTL falls back to the 5-minute default.
    assert request.ttl_seconds == 300
    assert issued.token == "head.sig"
    assert issued.org_id == ORG


def test_start_task_omits_unset_optionals(server):
    client, received = server

    client.start_task(
        bearer="t",
        org_id=ORG,
        task_id=TASK,
        session_id=SESSION,
        audience="accounts",
        scopes=[SCOPE],
        ttl=timedelta(minutes=10),
    )

    _, request, _ = received[0]
    assert request.ttl_seconds == 600
    assert not request.HasField("workspace_id")
    assert not request.HasField("project_id")
    assert request.actor_principal_id == ""


def test_exchange_audience_reissues_parent_per_audience(server):
    client, received = server
    parent = pb.IssuedWorkContext(token="head.sig", org_id=ORG)

    client.exchange_audience(
        bearer="user-token",
        parent=parent,
        audience="evidence",
        scopes=[SCOPE],
    )

    path, request, authorization = received[0]
    assert path == "/saas.accounts.v1.WorkContextService/ExchangeAudience"
    assert authorization == "Bearer user-token"
    assert request.org_id == ORG
    assert request.parent_work_context_token == "head.sig"
    assert request.audience == "evidence"
    assert list(request.attenuated_scopes) == [SCOPE]
    assert request.ttl_seconds == 300


def test_renew_keeps_audience_and_scopes_when_unset(server):
    client, received = server
    ctx = pb.IssuedWorkContext(token="head.sig", org_id=ORG)

    client.renew(bearer="actor-token", ctx=ctx)

    path, request, authorization = received[0]
    assert path == "/saas.accounts.v1.WorkContextService/RenewWorkContext"
    assert authorization == "Bearer actor-token"
    assert request.parent_work_context_token == "head.sig"
    assert not request.HasField("audience")
    assert list(request.attenuated_scopes) == []


def test_renew_applies_audience_and_scopes_when_set(server):
    client, received = server
    ctx = pb.IssuedWorkContext(token="head.sig", org_id=ORG)

    client.renew(bearer="actor-token", ctx=ctx, audience="accounts", scopes=[SCOPE])

    _, request, _ = received[0]
    assert request.audience == "accounts"
    assert list(request.attenuated_scopes) == [SCOPE]


@pytest.mark.parametrize("ttl", [timedelta(minutes=16), timedelta(seconds=-1)])
def test_ttl_outside_bounds_rejected_before_any_rpc(server, ttl):
    client, received = server

    with pytest.raises(ValueError):
        client.start_task(
            bearer="t",
            org_id=ORG,
            task_id=TASK,
            session_id=SESSION,
            audience="accounts",
            scopes=[SCOPE],
            ttl=ttl,
        )
    assert received == []


def test_transport_failure_surfaces_as_mint_error(server):
    client, received = server
    ctx = pb.IssuedWorkContext(token="head.sig", org_id=ORG)

    client._gateway.base_url = "http://127.0.0.1:1"

    with pytest.raises(work_context.WorkContextMintError) as excinfo:
        client.renew(bearer="actor-token", ctx=ctx)
    assert excinfo.value.procedure == "RenewWorkContext"
    assert isinstance(excinfo.value.__cause__, urllib.error.URLError)


def test_attach_stamps_header_on_mapping_and_request():
    ctx = pb.IssuedWorkContext(token="head.sig")

    headers: dict[str, str] = {}
    assert work_context.attach(headers, ctx) is headers
    assert headers[work_context.HEADER_NAME] == "head.sig"

    class Request:
        def __init__(self):
            self.headers: dict[str, str] = {}

    request = Request()
    work_context.attach(request, ctx)
    assert request.headers[work_context.HEADER_NAME] == "head.sig"


@pytest.mark.parametrize("token", ["", "no-dot", "too.many.dots"])
def test_attach_rejects_malformed_token(token):
    with pytest.raises(ValueError):
        work_context.attach({}, pb.IssuedWorkContext(token=token))


def test_start_task_sets_workspace_and_project_when_given(server):
    client, received = server

    client.start_task(
        bearer="user-token",
        org_id=ORG,
        task_id=TASK,
        session_id=SESSION,
        audience="accounts",
        scopes=[SCOPE],
        workspace_id="ws-1",
        project_id="proj-1",
    )

    _, request, _ = received[0]
    assert request.HasField("workspace_id") and request.workspace_id == "ws-1"
    assert request.HasField("project_id") and request.project_id == "proj-1"


def test_issued_token_round_trips_through_attach(server):
    client, _ = server

    issued = client.start_task(
        bearer="user-token",
        org_id=ORG,
        task_id=TASK,
        session_id=SESSION,
        audience="accounts",
        scopes=[SCOPE],
    )

    headers: dict[str, str] = {}
    work_context.attach(headers, issued)
    assert headers[work_context.HEADER_NAME] == issued.token


def test_renew_treats_empty_audience_as_keep_parent(server):
    client, received = server
    ctx = pb.IssuedWorkContext(token="head.sig", org_id=ORG)

    # An empty string must be handled like None: the optional audience field has
    # a server-side min_len=1, so a present empty value would be rejected.
    client.renew(bearer="actor-token", ctx=ctx, audience="")

    _, request, _ = received[0]
    assert not request.HasField("audience")


@pytest.mark.parametrize("ttl", [None, timedelta(0)])
def test_ttl_none_or_zero_defaults_to_five_minutes(server, ttl):
    client, received = server

    client.start_task(
        bearer="t",
        org_id=ORG,
        task_id=TASK,
        session_id=SESSION,
        audience="accounts",
        scopes=[SCOPE],
        ttl=ttl,
    )

    _, request, _ = received[0]
    assert request.ttl_seconds == 300


def test_gateway_without_bearer_keyword_surfaces_type_error_unmasked():
    # A gateway whose unary() predates the bearer seam is a call-contract bug,
    # not a mint failure — it must not be swallowed as WorkContextMintError.
    class LegacyGateway:
        def unary(self, procedure, request, response_type):
            raise AssertionError("unreachable: call should fail before this")

    client = work_context.new(LegacyGateway())
    with pytest.raises(TypeError):
        client.start_task(
            bearer="t",
            org_id=ORG,
            task_id=TASK,
            session_id=SESSION,
            audience="accounts",
            scopes=[SCOPE],
        )
