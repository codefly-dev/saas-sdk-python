"""Connect wire tests, using only the real generated host descriptors.

Until #1049 supplies the proto, the callable_contract tests fail explicitly.
The error mapper is independently exercised over the existing ListSources RPC;
that tests the same gateway/error seam without inventing replacement bindings.
"""

from __future__ import annotations

import base64
import doctest
import json
import threading
import time
import urllib.request
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, TypeVar
from urllib.error import HTTPError
from uuid import UUID

import pytest
from google.protobuf import json_format, message_factory
from google.protobuf.message import Message
from google.rpc.error_details_pb2 import BadRequest, ErrorInfo, RetryInfo

from saas_sdk import datasource as ds
from saas_sdk._gen import datasource_pb2 as pb

_M = TypeVar("_M", bound=Message)
_SERVICE = "/saas.accounts.v1.DatasourceService/"
_METHODS = (
    "InvokeSourceOperation",
    "LookupInvokeSourceOperation",
    "DeclareSourceOperations",
    "ListSourceOperations",
)


@dataclass
class State:
    received: list[tuple[str, dict[str, Any], dict[str, str]]] = field(
        default_factory=list
    )
    error: tuple[int, dict[str, Any]] | None = None
    operations: list[dict[str, Any]] = field(default_factory=list)
    unknown: bool = False
    lose_reply: bool = False
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)


class Gateway:
    """Fixture transport, not shipped by the SDK. No provider is contacted."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.work_context = "person-owned.opaque-signature"
        self.options: list[tuple[dict[str, str], float | None]] = []

    def unary(
        self,
        procedure: str,
        request: Message,
        response_type: type[_M],
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> _M:
        self.options.append((dict(headers or {}), timeout))
        http_headers = {
            "content-type": "application/proto",
            "connect-protocol-version": "1",
            "authorization": "Bearer fixture-person",
            "x-codefly-work-context": self.work_context,
        }
        http_headers.update(headers or {})
        http_request = urllib.request.Request(
            self.base_url + procedure,
            data=request.SerializeToString(),
            headers=http_headers,
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=timeout or 5) as response:
            payload = response.read()
        return response_type.FromString(payload)


def _status_name(response_type: type[Message], suffix: str) -> str:
    receipt = response_type.DESCRIPTOR.fields_by_name["receipt"].message_type
    assert receipt is not None
    status = receipt.fields_by_name["status"].enum_type
    assert status is not None
    return next(
        value.name for value in status.values if value.name.endswith("_" + suffix)
    )


@pytest.fixture
def connect() -> Iterator[tuple[Gateway, State]]:
    state = State()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            method = self.path.removeprefix(_SERVICE)
            methods = pb.DESCRIPTOR.services_by_name[
                "DatasourceService"
            ].methods_by_name
            if not self.path.startswith(_SERVICE) or method not in (
                *_METHODS,
                "ListSources",
            ):
                self.send_error(404)
                return
            descriptor = methods[method]
            request_type = message_factory.GetMessageClass(descriptor.input_type)
            response_type = message_factory.GetMessageClass(descriptor.output_type)
            request = request_type.FromString(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            data = json_format.MessageToDict(request, preserving_proto_field_name=True)
            state.received.append(
                (self.path, data, {k.lower(): v for k, v in self.headers.items()})
            )
            if state.lose_reply:
                self.close_connection = True
                return
            if state.error is not None:
                status, error = state.error
                self._respond(status, json.dumps(error).encode(), "application/json")
                return
            result: dict[str, Any] = {}
            if method in ("InvokeSourceOperation", "LookupInvokeSourceOperation"):
                effect_id = data["effect_id"]
                receipt = state.receipts.get(effect_id) or {
                    "effect_id": effect_id,
                    "status": _status_name(
                        response_type, "UNKNOWN" if state.unknown else "COMMITTED"
                    ),
                }
                if not state.unknown:
                    receipt.update(
                        committed_at="2026-10-09T18:00:00Z", provider_status=200
                    )
                state.receipts[effect_id] = receipt
                result["receipt"] = receipt
                if method == "InvokeSourceOperation":
                    result["output"] = {"invoices": [{"id": "invoice-1"}]}
            elif method == "DeclareSourceOperations":
                state.operations = data.get("operations", [])
            elif method == "ListSourceOperations":
                result["operations"] = state.operations
            response = json_format.ParseDict(result, response_type())
            self._respond(200, response.SerializeToString(), "application/proto")

        def _respond(self, status: int, payload: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True
    )
    thread.start()
    host, port = httpd.server_address[:2]
    assert isinstance(host, str)
    try:
        yield Gateway(f"http://{host}:{port}"), state
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def _detail(message: Message) -> dict[str, str]:
    return {
        "type": message.DESCRIPTOR.full_name,
        "value": base64.b64encode(message.SerializeToString())
        .decode("ascii")
        .rstrip("="),
    }


def _error(
    code: str, *details: Message, message: str = "host message"
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": [_detail(detail) for detail in details],
    }


@pytest.mark.callable_contract
def test_generated_contract_has_all_callable_methods() -> None:
    methods = pb.DESCRIPTOR.services_by_name["DatasourceService"].methods_by_name
    missing = set(_METHODS) - set(methods)
    assert not missing, (
        f"Regenerate from module-saas-starter#1049; missing RPCs: {sorted(missing)}. "
        "No fixture substitutes for the host proto."
    )


@pytest.mark.callable_contract
def test_invoke_mints_uuid7_forwards_authority_and_deadline(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    before = time.time_ns() // 1_000_000
    result = ds.invoke(
        gateway,
        "org-1",
        "source-1",
        "list_invoices",
        {"limit": 2},
        deadline=time.time() + 3.5,
    )
    after = time.time_ns() // 1_000_000
    effect_id = result.receipt.effect_id
    uuid = UUID(effect_id)
    assert uuid.version == 7
    assert before <= uuid.int >> 80 <= after
    assert result.output == {"invoices": [{"id": "invoice-1"}]}
    assert result.receipt.committed_at == datetime(2026, 10, 9, 18, tzinfo=timezone.utc)
    assert result.receipt.provider_status == 200
    path, request, headers = state.received[0]
    assert path == _SERVICE + "InvokeSourceOperation"
    assert request == {
        "org_id": "org-1",
        "source_id": "source-1",
        "operation": "list_invoices",
        "input": {"limit": 2},
        "effect_id": effect_id,
    }
    assert headers["authorization"] == "Bearer fixture-person"
    assert {k: v for k, v in headers.items() if k.startswith("x-codefly-")} == {
        "x-codefly-work-context": gateway.work_context,
        "x-codefly-effect-id": effect_id,
    }
    assert len(gateway.options) == 1
    headers_added, timeout = gateway.options[0]
    assert headers_added == {"x-codefly-effect-id": effect_id}
    assert timeout is not None and 0 < timeout <= 3.5


@pytest.mark.callable_contract
def test_same_id_reaches_host_twice_and_authority_is_not_cached(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    client = ds.new(gateway)
    input = {"nested": {"enabled": True, "items": [1, None, "a"]}}
    first = client.invoke(
        "org-1", "source-1", "create_invoice", input, effect_id="effect-1"
    )
    gateway.work_context = "renewed-person-context.unchanged-signature"
    second = client.invoke(
        "org-1", "source-1", "create_invoice", input, effect_id="effect-1"
    )
    assert len(state.received) == 2
    assert state.received[0][1] == state.received[1][1]
    assert state.received[1][2]["x-codefly-work-context"] == gateway.work_context
    assert first.receipt == second.receipt


@pytest.mark.callable_contract
def test_different_input_same_id_reaches_host_for_refusal(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    ds.invoke(
        gateway, "org", "source", "create_invoice", {"amount": 1}, effect_id="effect-1"
    )
    state.error = (
        400,
        _error("failed_precondition", message="effect ID input mismatch"),
    )
    with pytest.raises(ds.ProviderRefused, match="effect ID input mismatch"):
        ds.invoke(
            gateway,
            "org",
            "source",
            "create_invoice",
            {"amount": 2},
            effect_id="effect-1",
        )
    assert len(state.received) == 2
    assert state.received[0][1]["input"] != state.received[1][1]["input"]


@pytest.mark.callable_contract
def test_lookup_unknown_is_a_value(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    state.unknown = True
    outcome = ds.lookup(gateway, "org", "source", "effect-unknown")
    assert isinstance(outcome, ds.OutcomeUnknown)
    assert outcome.receipt.effect_id == "effect-unknown"
    assert outcome.receipt.committed_at is None
    assert outcome.receipt.provider_status is None
    assert gateway.options == [({}, None)]
    assert state.received[0][0] == _SERVICE + "LookupInvokeSourceOperation"


@pytest.mark.callable_contract
def test_lookup_committed_and_no_receipt_cache(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    first = ds.lookup(gateway, "org", "source", "effect-1")
    second = ds.lookup(gateway, "org", "source", "effect-1")
    assert isinstance(first, ds.Receipt)
    assert first == second
    assert len(state.received) == 2


@pytest.mark.callable_contract
def test_unavailable_invoke_keeps_minted_id_and_lookup_returns_it(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    state.error = (503, _error("unavailable", message="provider reply lost"))
    with pytest.raises(ds.OutcomeUnknown, match="provider reply lost") as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    effect_id = caught.value.effect_id
    assert UUID(effect_id).version == 7
    assert len(state.received) == 1  # no local retry
    with pytest.raises(HTTPError) as lookup_failure:
        ds.lookup(gateway, "org", "source", effect_id)
    assert lookup_failure.value.code == 503
    assert len(state.received) == 2


@pytest.mark.callable_contract
def test_lost_http_reply_retains_id_without_retry(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    state.lose_reply = True
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert len(state.received) == 1
    assert caught.value.effect_id == state.received[0][1]["effect_id"]


@pytest.mark.callable_contract
@pytest.mark.parametrize(
    ("code", "status", "expected"),
    [
        ("permission_denied", 403, ds.NotPermitted),
        ("not_found", 404, ds.UnknownOperation),
        ("invalid_argument", 400, ds.InputError),
        ("resource_exhausted", 429, ds.RateLimited),
        ("failed_precondition", 400, ds.ProviderRefused),
        ("unavailable", 503, ds.OutcomeUnknown),
        ("deadline_exceeded", 504, ds.OutcomeUnknown),
        ("canceled", 499, ds.OutcomeUnknown),
    ],
)
def test_invoke_typed_errors(
    connect: tuple[Gateway, State], code: str, status: int, expected: type[Exception]
) -> None:
    gateway, state = connect
    state.error = (status, _error(code, ErrorInfo(reason="DATASOURCE_RATE_LIMITED")))
    with pytest.raises(expected, match="host message"):
        ds.invoke(gateway, "org", "source", "create_invoice", {}, effect_id="effect-1")
    assert len(state.received) == 1


@pytest.mark.callable_contract
def test_declarations_round_trip(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    operations = [
        ds.Operation(
            name="list_invoices",
            method="GET",
            path="/customers/{customer_id}/invoices",
            query=["limit"],
            input={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "customer_id": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["customer_id"],
            },
            output={"type": "object"},
            effect=ds.Effect.READ_ONLY,
            max_output_bytes=65536,
        ),
        ds.Operation(
            name="create_invoice",
            method="POST",
            path="/invoices",
            input={"type": "object", "additionalProperties": False},
            output={"type": "object"},
            effect=ds.Effect.MUTATION,
            max_output_bytes=4096,
        ),
    ]
    ds.declare_operations(gateway, "org", "source", operations)
    assert ds.list_operations(gateway, "org", "source") == operations
    assert [request[0] for request in state.received] == [
        _SERVICE + "DeclareSourceOperations",
        _SERVICE + "ListSourceOperations",
    ]
    ds.declare_operations(gateway, "org", "source", [])
    assert ds.list_operations(gateway, "org", "source") == []


@pytest.mark.parametrize(
    ("code", "status", "expected"),
    [
        ("permission_denied", 403, ds.NotPermitted),
        ("not_found", 404, ds.UnknownOperation),
        ("invalid_argument", 400, ds.InputError),
        ("failed_precondition", 400, ds.ProviderRefused),
        ("unavailable", 503, ds.OutcomeUnknown),
        ("deadline_exceeded", 504, ds.OutcomeUnknown),
        ("canceled", 499, ds.OutcomeUnknown),
    ],
)
def test_connect_status_maps_without_retry(
    connect: tuple[Gateway, State], code: str, status: int, expected: type[Exception]
) -> None:
    gateway, state = connect
    state.error = (status, _error(code))
    with pytest.raises(expected, match="host message") as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"}, effect_id="effect-1")
    assert isinstance(caught.value.__cause__, HTTPError)
    assert len(state.received) == 1


def test_bad_request_pointer_and_credential_looking_message_unchanged(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    violation = BadRequest()
    violation.field_violations.add(
        field="/invoices/0/amount", description="must be positive"
    )
    message = "provider said Bearer fixture-secret-1234567890"
    state.error = (400, _error("invalid_argument", violation, message=message))
    with pytest.raises(ds.InputError) as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"})
    assert caught.value.pointer == "/invoices/0/amount"
    assert str(caught.value) == message


def test_retry_info_maps_to_absolute_reset(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    retry = RetryInfo()
    retry.retry_delay.FromTimedelta(timedelta(seconds=12.5))
    state.error = (
        429,
        _error(
            "resource_exhausted", ErrorInfo(reason="DATASOURCE_RATE_LIMITED"), retry
        ),
    )
    before = datetime.now(timezone.utc)
    with pytest.raises(ds.RateLimited) as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"})
    after = datetime.now(timezone.utc)
    assert caught.value.reset_at is not None
    assert (
        before + timedelta(seconds=12.5)
        <= caught.value.reset_at
        <= after + timedelta(seconds=12.5)
    )
    assert len(state.received) == 1


def test_host_reset_at_takes_precedence(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    info = ErrorInfo(
        reason="DATASOURCE_RATE_LIMITED", metadata={"reset_at": "2026-10-09T18:05:00Z"}
    )
    retry = RetryInfo()
    retry.retry_delay.seconds = 1
    state.error = (429, _error("resource_exhausted", info, retry))
    with pytest.raises(ds.RateLimited) as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"})
    assert caught.value.reset_at == datetime(2026, 10, 9, 18, 5, tzinfo=timezone.utc)


def test_provider_status_comes_from_details_not_connect_http_status(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    state.error = (
        400,
        _error("failed_precondition", ErrorInfo(metadata={"provider_status": "401"})),
    )
    with pytest.raises(ds.ProviderRefused) as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"})
    assert caught.value.status == 401


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (401, _error("unauthenticated")),
        (500, _error("internal")),
        (500, _error("permission_denied")),
        (429, _error("resource_exhausted", ErrorInfo(reason="SOME_OTHER_QUOTA"))),
        (400, {"code": 42}),
    ],
)
def test_other_gateway_errors_propagate(
    connect: tuple[Gateway, State], status: int, payload: dict[str, Any]
) -> None:
    gateway, state = connect
    state.error = (status, payload)
    with pytest.raises(HTTPError) as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"})
    assert caught.value.code == status
    assert len(state.received) == 1


def test_malformed_details_do_not_destroy_typed_status_or_host_message(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    payload = _error("invalid_argument")
    payload["details"] = [
        {"type": "google.rpc.BadRequest", "value": "not base64!"},
        None,
    ]
    state.error = (400, payload)
    with pytest.raises(ds.InputError, match="host message") as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"})
    assert caught.value.pointer == ""


@pytest.mark.parametrize("deadline", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_deadline_never_dispatches(
    connect: tuple[Gateway, State], deadline: float
) -> None:
    gateway, state = connect
    with pytest.raises(ValueError, match="deadline"):
        ds.invoke(gateway, "org", "source", "list_invoices", {}, deadline=deadline)
    assert not state.received


@pytest.mark.parametrize("effect_id", ["", "bad\r\nheader", "bad id", "é"])
def test_invalid_effect_id_never_dispatches(
    connect: tuple[Gateway, State], effect_id: str
) -> None:
    gateway, state = connect
    with pytest.raises(ValueError, match="effect_id"):
        ds.invoke(gateway, "org", "source", "list_invoices", {}, effect_id=effect_id)
    assert not state.received


def test_non_json_input_is_an_input_error(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    with pytest.raises(ds.InputError):
        ds.invoke(gateway, "org", "source", "create_invoice", {"unsupported": object()})
    assert not state.received


def test_receipt_enum_names_match_go() -> None:
    assert [status.value for status in ds.ReceiptStatus] == [
        "COMMITTED",
        "REFUSED",
        "UNKNOWN",
    ]
    assert [effect.value for effect in ds.Effect] == ["READ_ONLY", "MUTATION"]


@pytest.mark.callable_contract
def test_readme_example(connect: tuple[Gateway, State]) -> None:
    gateway, _ = connect
    text = (Path(__file__).parents[1] / "README.md").read_text()
    test = doctest.DocTestParser().get_doctest(
        text, {"gateway": gateway}, "README", "README.md", 0
    )
    assert test.examples, "the call-half example must remain executable"
    runner = doctest.DocTestRunner()
    result = runner.run(test)
    assert result.failed == 0
