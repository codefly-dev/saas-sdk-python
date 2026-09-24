"""End-to-end audit facade tests over a real Connect-unary HTTP round-trip.

Same boundary as the datasource and Work Context mint tests: a real HTTP server
keyed by the *actual* ``/saas.accounts.v1.AuditService/<Method>`` procedures, so a
wrong procedure string 404s instead of being echoed back by a stub. The gateway
reproduces ``solution_runtime.Gateway`` — bound to the caller's bearer, raising
urllib's ``HTTPError`` on a Connect error — so the refusal mapping is exercised
against the error shape the runtime actually produces.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from google.protobuf.struct_pb2 import Struct
from google.protobuf.timestamp_pb2 import Timestamp

from saas_sdk import audit
from saas_sdk._gen import audit_pb2 as pb


class Gateway:
    """Real Connect-unary gateway bound to one caller's bearer, as the runtime's."""

    def __init__(self, base_url: str, bearer: str) -> None:
        self.base_url = base_url
        self.bearer = bearer

    def unary(self, procedure, request, response_type):
        http_request = urllib.request.Request(
            f"{self.base_url}{procedure}",
            data=request.SerializeToString(),
            headers={
                "content-type": "application/proto",
                "connect-protocol-version": "1",
                "authorization": self.bearer,
            },
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=10) as http_response:
            body = http_response.read()
        message = response_type()
        message.ParseFromString(body)
        return message


ORG = "11111111-1111-1111-1111-111111111111"
CREATED = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _event_page(req):
    payload = Struct()
    payload.update({"item_id": "item-1", "amount": 3})
    created = Timestamp()
    created.FromDatetime(CREATED)
    return pb.QueryAuditLogResponse(
        events=[
            pb.AuditEvent(
                id="evt-1",
                actor_id="person-1",
                org_id=req.org_id,
                event_type="example.item.created",
                category="example",
                schema_version=2,
                payload=payload,
                created_at=created,
            )
        ],
        next_page_token="cursor-2",
        total_count=7,
    )


def _buckets(req):
    return pb.AggregateAuditLogResponse(
        buckets=[
            pb.AuditAggregateBucket(
                key="example.item.created",
                count=4,
                keys=["example.item.created", "2026-01-01"],
                metrics={"count": 4.0, "sum_amount": 12.5},
            )
        ]
    )


def _types(req):
    return pb.ListAuditEventTypesResponse(
        types=[
            pb.AuditEventType(name="example.item.created", version=1, category="example"),
            pb.AuditEventType(name="example.item.deleted", version=1, deprecated=True),
        ]
    )


_ROUTES = {
    "/saas.accounts.v1.AuditService/QueryAuditLog": (pb.QueryAuditLogRequest, _event_page),
    "/saas.accounts.v1.AuditService/AggregateAuditLog": (pb.AggregateAuditLogRequest, _buckets),
    "/saas.accounts.v1.AuditService/ListAuditEventTypes": (
        pb.ListAuditEventTypesRequest,
        _types,
    ),
}


@pytest.fixture
def server():
    received: list[tuple[str, object, str]] = []
    # (status, Connect error body) the next request answers with instead of a
    # success, set by a test to drive the error paths through real HTTP.
    failure: dict[str, tuple[int, dict]] = {}

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
            if "next" in failure:
                status, error = failure.pop("next")
                self._reply(status, "application/json", json.dumps(error).encode())
                return
            self._reply(200, "application/proto", respond(request).SerializeToString())

        def _reply(self, status, content_type, payload):
            self.send_response(status)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    client = audit.new(Gateway(f"http://{host}:{port}", "Bearer person-token"))
    try:
        yield client, received, failure
    finally:
        httpd.shutdown()


def test_query_maps_filters_and_returns_the_page(server):
    client, received, _ = server
    since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # A non-UTC zone is converted, not read as UTC wall-clock time.
    until = datetime(2026, 1, 31, 19, 0, tzinfo=timezone(timedelta(hours=-5)))

    page = client.query(
        ORG,
        actor_id="person-1",
        event_type="example.item.created",
        category="example",
        resource="item",
        resource_id="item-1",
        payload_contains={"item_id": "item-1"},
        from_=since,
        to=until,
        page_size=20,
        page_token="cursor-1",
    )

    path, request, authorization = received[0]
    assert path == "/saas.accounts.v1.AuditService/QueryAuditLog"
    # Made as the signed-in person: the gateway's caller-bound bearer, untouched.
    assert authorization == "Bearer person-token"
    assert request.org_id == ORG
    assert request.actor_id == "person-1"
    assert request.event_type == "example.item.created"
    assert request.category == "example"
    assert request.resource == "item"
    assert request.resource_id == "item-1"
    assert dict(request.payload_contains) == {"item_id": "item-1"}
    assert getattr(request, "from").ToDatetime(tzinfo=timezone.utc) == since
    assert request.to.ToDatetime(tzinfo=timezone.utc) == datetime(
        2026, 2, 1, 0, 0, tzinfo=timezone.utc
    )
    assert request.page_size == 20
    assert request.page_token == "cursor-1"
    # The deprecated `action` filter is never sent; event_type supersedes it.
    assert request.action == ""

    assert isinstance(page, audit.QueryAuditLogResponse)
    assert page.next_page_token == "cursor-2"
    assert page.total_count == 7
    [event] = page.events
    assert isinstance(event, audit.AuditEvent)
    assert event.id == "evt-1"
    assert event.org_id == ORG
    assert event.event_type == "example.item.created"
    assert event.schema_version == 2
    assert dict(event.payload) == {"item_id": "item-1", "amount": 3}
    assert event.created_at.ToDatetime(tzinfo=timezone.utc) == CREATED


def test_query_defaults_send_a_valid_page_size_and_no_window(server):
    client, received, _ = server

    client.query(ORG)

    _, request, _ = received[0]
    # The server rejects page_size 0 (0 < page_size <= 100), so the facade never
    # sends it unset.
    assert request.page_size == audit.DEFAULT_PAGE_SIZE == 50
    assert not request.HasField("from")
    assert not request.HasField("to")
    assert dict(request.payload_contains) == {}
    assert request.page_token == ""


@pytest.mark.parametrize("field", ["from_", "to"])
def test_naive_datetime_rejected_before_any_rpc(server, field):
    client, received, _ = server

    with pytest.raises(ValueError, match="timezone-aware"):
        client.query(ORG, **{field: datetime(2026, 1, 1)})
    with pytest.raises(ValueError, match="timezone-aware"):
        client.aggregate(ORG, **{field: datetime(2026, 1, 1)})
    assert received == []


def test_aggregate_maps_the_spec_and_returns_the_whole_response(server):
    client, received, _ = server
    metrics = [
        audit.AuditMetric(op="count"),
        audit.AuditMetric(op="sum", field="payload:amount", alias="sum_amount"),
        audit.AuditMetric(op="percentile", field="payload:amount", percentile=0.95),
    ]
    derived = [audit.AuditDerivedMetric(alias="avg", numerator="sum_amount", denominator="count")]

    response = client.aggregate(
        ORG,
        actor_id="person-1",
        event_type="example.item.created",
        category="example",
        resource="item",
        from_=datetime(2026, 1, 1, tzinfo=timezone.utc),
        to=datetime(2026, 2, 1, tzinfo=timezone.utc),
        group_bys=["event_type", "time"],
        bucket="day",
        metrics=metrics,
        derived=derived,
    )

    path, request, authorization = received[0]
    assert path == "/saas.accounts.v1.AuditService/AggregateAuditLog"
    assert authorization == "Bearer person-token"
    assert request.org_id == ORG
    assert request.actor_id == "person-1"
    assert request.event_type == "example.item.created"
    assert request.category == "example"
    assert request.resource == "item"
    assert request.HasField("from") and request.HasField("to")
    assert list(request.group_bys) == ["event_type", "time"]
    # group_bys supersedes the single group_by; the facade only sends the list.
    assert request.group_by == ""
    assert request.bucket == "day"
    assert list(request.metrics) == metrics
    assert list(request.derived) == derived

    assert isinstance(response, audit.AggregateAuditLogResponse)
    [bucket] = response.buckets
    assert isinstance(bucket, audit.AuditAggregateBucket)
    assert bucket.key == "example.item.created"
    assert bucket.count == 4
    assert list(bucket.keys) == ["example.item.created", "2026-01-01"]
    assert dict(bucket.metrics) == {"count": 4.0, "sum_amount": 12.5}


def test_aggregate_defaults_send_an_empty_spec(server):
    client, received, _ = server

    client.aggregate(ORG)

    _, request, _ = received[0]
    assert request == pb.AggregateAuditLogRequest(org_id=ORG)


def test_list_event_types_returns_bare_list(server):
    client, received, _ = server

    types = client.list_event_types()

    path, request, authorization = received[0]
    assert path == "/saas.accounts.v1.AuditService/ListAuditEventTypes"
    assert authorization == "Bearer person-token"
    assert request == pb.ListAuditEventTypesRequest()
    assert [(t.name, t.deprecated) for t in types] == [
        ("example.item.created", False),
        ("example.item.deleted", True),
    ]
    assert all(isinstance(t, audit.AuditEventType) for t in types)


_CALLS = {
    "QueryAuditLog": lambda client: client.query(ORG),
    "AggregateAuditLog": lambda client: client.aggregate(ORG),
    "ListAuditEventTypes": lambda client: client.list_event_types(),
}


@pytest.mark.parametrize("method", sorted(_CALLS))
@pytest.mark.parametrize(
    "status, code",
    [(401, audit.UNAUTHENTICATED), (403, audit.PERMISSION_DENIED)],
)
def test_refusal_raises_audit_denied(server, method, status, code):
    client, _, failure = server
    failure["next"] = (status, {"code": code, "message": "not a member of the organization"})

    with pytest.raises(audit.AuditDenied) as excinfo:
        _CALLS[method](client)

    assert excinfo.value.procedure == method
    assert excinfo.value.code == code
    # The gateway's own error stays reachable for diagnosis.
    assert isinstance(excinfo.value.__cause__, urllib.error.HTTPError)


@pytest.mark.parametrize(
    "status, body",
    [
        (503, {"code": "unavailable", "message": "try again"}),
        (400, {"code": "invalid_argument", "message": "page_size"}),
        (500, {"code": "internal"}),
        # Incoherent pairs are not refusals: Connect never sends these.
        (403, {"code": "unauthenticated"}),
        (401, {"code": "permission_denied"}),
        (403, {"message": "no code"}),
    ],
)
def test_other_error_responses_surface_as_the_gateways_error(server, status, body):
    client, _, failure = server
    failure["next"] = (status, body)

    with pytest.raises(urllib.error.HTTPError) as excinfo:
        client.query(ORG)
    assert not isinstance(excinfo.value, audit.AuditDenied)
    assert excinfo.value.code == status


def test_non_json_refusal_status_surfaces_as_the_gateways_error():
    class HTMLGateway:
        def unary(self, procedure, request, response_type):
            raise urllib.error.HTTPError(procedure, 403, "Forbidden", None, None)

    with pytest.raises(urllib.error.HTTPError):
        audit.new(HTMLGateway()).list_event_types()


def test_transport_failure_is_not_a_refusal(server):
    client, _, _ = server
    client._gateway.base_url = "http://127.0.0.1:1"

    with pytest.raises(urllib.error.URLError) as excinfo:
        client.list_event_types()
    assert not isinstance(excinfo.value, audit.AuditDenied)


def test_gateway_raising_audit_denied_is_not_double_wrapped():
    denied = audit.AuditDenied("QueryAuditLog", audit.PERMISSION_DENIED)

    class DenyingGateway:
        def unary(self, procedure, request, response_type):
            raise denied

    with pytest.raises(audit.AuditDenied) as excinfo:
        audit.new(DenyingGateway()).query(ORG)
    assert excinfo.value is denied
