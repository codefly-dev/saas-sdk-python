"""Connect wire tests, using only the real generated host descriptors.

The fake handlers use the exact messages regenerated from host PR #1052.
No fixture replaces the generated contract or the SDK's gateway call seam.
"""

from __future__ import annotations

import base64
import doctest
import gzip
import json
import threading
import time
import urllib.request
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import Message as Headers
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any, TypeVar, cast
from urllib.error import HTTPError
from uuid import UUID

import pytest
from google.protobuf import json_format, message_factory
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.rpc.error_details_pb2 import BadRequest, ErrorInfo, RetryInfo

from saas_sdk import datasource as ds
from saas_sdk._datasource_errors import map_error
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
    raw_error: tuple[int, bytes, str] | None = None
    error_content_encoding: str | None = None
    operations: list[dict[str, Any]] = field(default_factory=list)
    unknown: bool = False
    lose_reply: bool = False
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    output_json: str = '{"invoices":[{"id":"invoice-1"}]}'
    response: dict[str, Any] | None = None


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
        # Go sends UTF-8 header bytes. urllib uses a Latin-1 str interface.
        http_headers.update(
            {k: v.encode("utf-8").decode("latin-1") for k, v in (headers or {}).items()}
        )
        http_request = urllib.request.Request(
            self.base_url + procedure,
            data=request.SerializeToString(),
            headers=http_headers,
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=timeout or 5) as response:
            payload = response.read()
        return response_type.FromString(payload)


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
            if state.raw_error is not None:
                self._respond(*state.raw_error)
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
                    "status": "unknown" if state.unknown else "committed",
                    "output_json": "{}" if state.unknown else state.output_json,
                }
                if not state.unknown:
                    receipt.update(
                        committed_at="2026-10-09T18:00:00Z", provider_status=200
                    )
                state.receipts[effect_id] = receipt
                result["receipt"] = receipt
                result["output_json"] = receipt["output_json"]
            elif method == "DeclareSourceOperations":
                state.operations = data.get("operations", [])
            elif method == "ListSourceOperations":
                result["operations"] = state.operations
            response = json_format.ParseDict(
                state.response if state.response is not None else result,
                response_type(),
            )
            self._respond(200, response.SerializeToString(), "application/proto")

        def _respond(self, status: int, payload: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("content-type", content_type)
            if state.error_content_encoding is not None:
                self.send_header("content-encoding", state.error_content_encoding)
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


def test_generated_contract_has_all_callable_methods() -> None:
    methods = pb.DESCRIPTOR.services_by_name["DatasourceService"].methods_by_name
    missing = set(_METHODS) - set(methods)
    assert not missing, (
        f"Regenerate from module-saas-starter#1049; missing RPCs: {sorted(missing)}. "
        "No fixture substitutes for the host proto."
    )


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
        "input_json": '{"limit":2}',
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


def test_different_input_same_id_reaches_host_for_refusal(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    ds.invoke(
        gateway, "org", "source", "create_invoice", {"amount": 1}, effect_id="effect-1"
    )
    state.error = (
        400,
        _error(
            "failed_precondition",
            ErrorInfo(reason="SOURCE_EFFECT_REUSED"),
            message="source operation refused",
        ),
    )
    with pytest.raises(ds.EffectReused, match="source operation refused") as caught:
        ds.invoke(
            gateway,
            "org",
            "source",
            "create_invoice",
            {"amount": 2},
            effect_id="effect-1",
        )
    assert caught.value.effect_id == "effect-1"
    assert len(state.received) == 2
    assert state.received[0][1]["input_json"] != state.received[1][1]["input_json"]


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
    assert state.received[0][1] == {"effect_id": "effect-unknown"}


def test_lookup_committed_and_no_receipt_cache(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    first = ds.lookup(gateway, "org", "source", "effect-1")
    second = ds.lookup(gateway, "org", "source", "effect-1")
    assert isinstance(first, ds.Receipt)
    assert first == second
    assert len(state.received) == 2


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
    outcome = ds.lookup(gateway, "org", "source", effect_id)
    assert isinstance(outcome, ds.OutcomeUnknown)
    assert outcome.effect_id == effect_id
    assert str(outcome) == "provider reply lost"
    assert len(state.received) == 2


def test_lost_http_reply_retains_id_without_retry(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    state.lose_reply = True
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert len(state.received) == 1
    assert caught.value.effect_id == state.received[0][1]["effect_id"]


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
    reason = (
        "SOURCE_PROVIDER_REFUSED"
        if code == "failed_precondition"
        else "DATASOURCE_RATE_LIMITED"
    )
    state.error = (status, _error(code, ErrorInfo(reason=reason)))
    with pytest.raises(expected, match="host message") as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert isinstance(caught.value, ds.DatasourceError)
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert caught.value.receipt is not None
    assert caught.value.receipt.effect_id == caught.value.effect_id
    assert len(state.received) == 1


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
        ("failed_precondition", 400, ds.OperationRefused),
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


def test_pinned_host_provider_refusal_has_no_status(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    state.error = (
        400,
        _error("failed_precondition", ErrorInfo(reason="SOURCE_PROVIDER_REFUSED")),
    )
    with pytest.raises(ds.ProviderRefused) as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"})
    assert caught.value.status is None


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (401, _error("unauthenticated")),
        (500, _error("internal")),
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
    assert json.loads(caught.value.read()) == payload
    assert len(state.received) == 1


def test_invalid_protobuf_details_preserve_typed_status_and_host_message(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    payload = _error("invalid_argument")
    payload["details"] = [
        {
            "type": "google.rpc.BadRequest",
            "value": base64.b64encode(b"\x80").decode("ascii"),
        },
        None,
    ]
    state.error = (400, payload)
    with pytest.raises(ds.InputError, match="host message") as caught:
        ds._rpc(gateway, "ListSources", {"org_id": "org"})
    assert caught.value.pointer == ""


@pytest.mark.parametrize(
    "deadline", [0.0, -1.0, float("nan"), float("inf"), -float("inf")]
)
def test_invalid_deadline_never_dispatches(
    connect: tuple[Gateway, State], deadline: float
) -> None:
    gateway, state = connect
    with pytest.raises(ds.InputError, match="deadline") as caught:
        ds.invoke(gateway, "org", "source", "list_invoices", {}, deadline=deadline)
    assert caught.value.effect_id is None
    assert caught.value.receipt is None
    assert not gateway.options
    assert not state.received


@pytest.mark.parametrize(
    "effect_id",
    [
        "",
        "bad\r\nheader",
        "bad\x00id",
        "bad\tid",
        "bad\x7fid",
        " id",
        "id ",
        " ",
        "a" * 129,
        "é" * 65,
        "\ud800",
    ],
)
def test_invalid_effect_id_never_dispatches(
    connect: tuple[Gateway, State], effect_id: str
) -> None:
    gateway, state = connect
    with pytest.raises(ds.InputError, match="effect_id") as caught:
        ds.invoke(gateway, "org", "source", "list_invoices", {}, effect_id=effect_id)
    assert caught.value.effect_id is None
    assert not state.received


def test_non_json_input_is_an_input_error(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    with pytest.raises(ds.InputError):
        ds.invoke(gateway, "org", "source", "create_invoice", {"unsupported": object()})
    assert not state.received


def test_receipt_enum_names_match_go() -> None:
    assert [status.value for status in ds.ReceiptStatus] == [
        "COMMITTED",
        "UNKNOWN",
        "NOT_ATTEMPTED",
    ]
    assert [effect.value for effect in ds.Effect] == ["READ_ONLY", "MUTATION"]


def test_json_payload_preserves_large_integers_and_unicode(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    value = {
        "invoice": 9007199254740993,
        "customer": "café",
        "nested": [None, True, {"x": 7}],
    }
    state.output_json = json.dumps(value)
    result = ds.invoke(gateway, "org", "source", "create_invoice", value)
    assert json.loads(state.received[0][1]["input_json"]) == value
    assert "input" not in state.received[0][1]
    assert result.output == value
    assert isinstance(result.output["invoice"], int)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_input_is_refused_before_dispatch(
    connect: tuple[Gateway, State], value: float
) -> None:
    gateway, state = connect
    with pytest.raises(ds.InputError):
        ds.invoke(gateway, "org", "source", "create_invoice", {"amount": value})
    assert not state.received


@pytest.mark.parametrize("output", ["", "[]", "null", "42", '{"x":NaN}', "{} {}"])
def test_invalid_output_does_not_lose_effect_id(
    connect: tuple[Gateway, State], output: str
) -> None:
    gateway, state = connect
    state.output_json = output
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert len(state.received) == 1


@pytest.mark.parametrize(
    ("code", "status"), [("deadline_exceeded", 504), ("canceled", 499)]
)
def test_lookup_other_transport_failures_still_raise(
    connect: tuple[Gateway, State], code: str, status: int
) -> None:
    gateway, state = connect
    state.error = status, _error(code)
    with pytest.raises(HTTPError) as caught:
        ds.lookup(gateway, "org", "source", "effect-1")
    assert caught.value.code == status
    assert len(state.received) == 1


def test_generated_payloads_are_strings_and_lookup_selects_effect() -> None:
    assert (
        pb.InvokeSourceOperationRequest.DESCRIPTOR.fields_by_name["input_json"].type
        == FieldDescriptor.TYPE_STRING
    )
    assert (
        pb.InvokeSourceOperationResponse.DESCRIPTOR.fields_by_name["output_json"].type
        == FieldDescriptor.TYPE_STRING
    )
    assert (
        pb.SourceOperationReceipt.DESCRIPTOR.fields_by_name["output_json"].type
        == FieldDescriptor.TYPE_STRING
    )
    assert list(pb.LookupInvokeSourceOperationRequest.DESCRIPTOR.fields_by_name) == [
        "effect_id"
    ]


@pytest.mark.parametrize("status", ["refused", "COMMITTED", "future_status"])
def test_unsupported_receipt_status_keeps_effect_unknown(
    connect: tuple[Gateway, State], status: str
) -> None:
    gateway, state = connect
    state.receipts["effect-1"] = {
        "effect_id": "effect-1",
        "status": status,
        "output_json": "{}",
    }
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {}, effect_id="effect-1")
    assert caught.value.effect_id == "effect-1"
    assert len(state.received) == 1


def test_host_lost_mutation_reason_is_unknown_with_minted_id(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    message = (
        "source operation outcome is unknown; this effect will not be dispatched again"
    )
    state.error = (
        400,
        _error(
            "failed_precondition",
            ErrorInfo(reason="SOURCE_OPERATION_OUTCOME_UNKNOWN"),
            message=message,
        ),
    )
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert str(caught.value) == message
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert UUID(caught.value.effect_id).version == 7
    assert not isinstance(caught.value, ds.ProviderRefused)
    assert len(state.received) == 1


@pytest.mark.parametrize(
    "reason",
    [
        "SOURCE_DECLARATION_CHANGED",
        "SOURCE_REAUTH_REQUIRED",
        "SOURCE_EFFECT_BINDING_CHANGED",
        "SOURCE_OUTPUT_REFUSED",
        "",
    ],
)
def test_nonprovider_preconditions_retain_host_reason(
    connect: tuple[Gateway, State], reason: str
) -> None:
    gateway, state = connect
    state.error = (
        400,
        _error(
            "failed_precondition",
            ErrorInfo(reason=reason),
            message="source operation refused",
        ),
    )
    with pytest.raises(ds.OperationRefused) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert caught.value.reason == reason
    assert not isinstance(caught.value, ds.ProviderRefused)


@pytest.mark.parametrize("status", [500, 502, 503, 504])
@pytest.mark.parametrize(
    "body", [b"upstream request timeout", b"<html>upstream unavailable</html>"]
)
def test_proxy_5xx_retains_effect_id_without_retry(
    connect: tuple[Gateway, State], status: int, body: bytes
) -> None:
    gateway, state = connect
    state.raw_error = status, body, "text/plain"
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert UUID(caught.value.effect_id).version == 7
    assert len(state.received) == 1


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


@pytest.mark.parametrize(
    "effect_id", ["bad id", "facture-é", "发票-1", "a" * 128, "é" * 64]
)
def test_effect_id_accepts_host_utf8_profile(
    connect: tuple[Gateway, State], effect_id: str
) -> None:
    gateway, state = connect
    result = ds.invoke(
        gateway, "org", "source", "create_invoice", {}, effect_id=effect_id
    )
    assert result.receipt.effect_id == effect_id
    assert state.received[0][1]["effect_id"] == effect_id
    assert (
        state.received[0][2]["x-codefly-effect-id"].encode("latin-1").decode("utf-8")
        == effect_id
    )


def test_absent_effect_can_be_explicitly_reinvoked_with_same_id(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    state.error = (503, _error("unavailable"))
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {"amount": 2})
    effect_id = caught.value.effect_id
    state.error = (404, _error("not_found", message="source effect not found"))
    outcome = ds.lookup(gateway, "org", "source", effect_id)
    assert isinstance(outcome, ds.EffectNotFound)
    assert outcome.effect_id == effect_id
    assert outcome.receipt.status is ds.ReceiptStatus.NOT_ATTEMPTED
    assert outcome.receipt.output is None
    assert str(outcome) == "source effect not found"
    assert len(state.received) == 2
    state.error = None
    result = ds.invoke(
        gateway,
        "org",
        "source",
        "create_invoice",
        {"amount": 2},
        effect_id=outcome.effect_id,
    )
    assert result.receipt.effect_id == effect_id
    assert len(state.received) == 3
    assert state.received[0][1] == state.received[2][1]


def test_lookup_retains_committed_output(connect: tuple[Gateway, State]) -> None:
    gateway, state = connect
    result = ds.invoke(gateway, "org", "source", "create_invoice", {})
    receipt = ds.lookup(gateway, "org", "source", result.receipt.effect_id)
    assert isinstance(receipt, ds.Receipt)
    assert receipt.output == result.output
    assert len(state.received) == 2


def test_operation_description_and_read_only_digest(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    operation = ds.Operation(
        "list_invoices",
        "GET",
        "/invoices",
        ds.Effect.READ_ONLY,
        description="List invoices",
        digest="caller-digest-ignored",
    )
    ds.declare_operations(gateway, "org", "source", [operation])
    assert state.operations[0]["description"] == operation.description
    assert "digest" not in state.operations[0]
    state.operations[0]["digest"] = "host-digest"
    [listed] = ds.list_operations(gateway, "org", "source")
    assert listed.description == operation.description
    assert listed.digest == "host-digest"


@pytest.mark.parametrize("max_output_bytes", [-1, 2**32])
def test_out_of_range_declaration_is_typed_before_dispatch(
    connect: tuple[Gateway, State], max_output_bytes: int
) -> None:
    gateway, state = connect
    operation = ds.Operation(
        "list_invoices",
        "GET",
        "/invoices",
        ds.Effect.READ_ONLY,
        max_output_bytes=max_output_bytes,
    )
    with pytest.raises(ds.InputError):
        ds.declare_operations(gateway, "org", "source", [operation])
    assert not state.received


def test_invalid_local_operation_effect_is_typed(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    operation = ds.Operation(
        "list_invoices", "GET", "/invoices", cast(ds.Effect, "INVALID")
    )
    with pytest.raises(ds.InputError, match="effect"):
        ds.declare_operations(gateway, "org", "source", [operation])
    assert not state.received


@pytest.mark.parametrize("effect", ["EFFECT_UNSPECIFIED", 42])
def test_invalid_host_operation_effect_is_typed(
    connect: tuple[Gateway, State], effect: str | int
) -> None:
    gateway, state = connect
    state.operations = [
        {
            "name": "list_invoices",
            "method": "GET",
            "path": "/invoices",
            "effect": effect,
        }
    ]
    with pytest.raises(ds.DatasourceError, match="unsupported operation effect"):
        ds.list_operations(gateway, "org", "source")


@pytest.mark.parametrize(
    "receipt",
    [None, {}, {"effect_id": "wrong", "status": "committed", "output_json": "{}"}],
)
def test_invalid_lookup_receipt_is_typed(
    connect: tuple[Gateway, State], receipt: dict[str, Any] | None
) -> None:
    gateway, state = connect
    state.response = {} if receipt is None else {"receipt": receipt}
    with pytest.raises(ds.DatasourceError, match="invalid lookup receipt") as caught:
        ds.lookup(gateway, "org", "source", "effect-1")
    assert caught.value.effect_id == "effect-1"


def test_legacy_gateway_still_connects_but_cannot_invoke() -> None:
    class LegacyGateway:
        calls = 0

        def unary(
            self, procedure: str, request: Message, response_type: type[_M]
        ) -> _M:
            self.calls += 1
            return response_type()

    gateway = LegacyGateway()
    client = ds.new(gateway)
    assert client.list_sources("org") == []
    assert gateway.calls == 1
    with pytest.raises(TypeError, match="OperationGateway.*upgrade the runtime"):
        client.invoke("org", "source", "create_invoice", {})
    assert gateway.calls == 1


def test_nonconnect_dispatch_error_keeps_minted_id_and_readable_cause(
    connect: tuple[Gateway, State],
) -> None:
    gateway, state = connect
    body = b"unauthenticated proxy response"
    state.raw_error = (401, body, "text/plain")
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert caught.value.receipt.effect_id == caught.value.effect_id
    assert isinstance(caught.value.__cause__, HTTPError)
    assert caught.value.__cause__.read() == body
    assert len(state.received) == 1


@pytest.mark.parametrize(
    "body",
    [b"plain proxy error", b'{"code":"unauthenticated","message":"no bearer"}', b"[]"],
)
def test_error_mapper_preserves_original_body_and_closes_stream(body: bytes) -> None:
    original = BytesIO(body)
    error = HTTPError("http://example.com", 401, "Unauthorized", Headers(), original)
    # Runtime callers may already have caused tempfile's wrapper to cache read.
    assert error.read(0) == b""
    assert map_error(error) is None
    assert original.closed
    with error:
        assert error.read() == body
        assert error.code == 401
        assert error.url == "http://example.com"
    assert error.closed


def test_error_mapper_accepts_bodyless_error() -> None:
    error = HTTPError("http://example.com", 401, "Unauthorized", Headers(), None)
    assert map_error(error) is None
    assert error.read() == b""
    error.close()


@pytest.mark.parametrize(
    "message", ["source effect not found", "source operation not found"]
)
def test_lookup_not_found_preserves_host_ambiguity(
    connect: tuple[Gateway, State], message: str
) -> None:
    gateway, state = connect
    state.error = (404, _error("not_found", message=message))
    outcome = ds.lookup(gateway, "org", "source", "effect-1")
    assert isinstance(outcome, ds.EffectNotFound)
    assert str(outcome) == message
    assert outcome.effect_id == "effect-1"
    assert len(state.received) == 1


@pytest.mark.parametrize("proxy", [False, True])
def test_lookup_unknown_errors_are_always_values(
    connect: tuple[Gateway, State], proxy: bool
) -> None:
    gateway, state = connect
    if proxy:
        state.raw_error = (503, b"upstream unavailable", "text/plain")
    else:
        state.error = (
            400,
            _error(
                "failed_precondition",
                ErrorInfo(reason="SOURCE_OPERATION_OUTCOME_UNKNOWN"),
            ),
        )
    outcome = ds.lookup(gateway, "org", "source", "effect-1")
    assert isinstance(outcome, ds.OutcomeUnknown)
    assert outcome.effect_id == "effect-1"
    assert len(state.received) == 1


@pytest.mark.parametrize(
    "status",
    [400, 401, 403, 404, 408, 409, 418, 422, 429, 499, 500, 501, 502, 503, 504, 599],
)
@pytest.mark.parametrize("lookup", [False, True])
def test_nonconnect_http_errors_leave_effect_unknown(
    connect: tuple[Gateway, State], status: int, lookup: bool
) -> None:
    gateway, state = connect
    state.raw_error = (status, b"proxy rejected the exchange", "text/plain")
    if lookup:
        outcome = ds.lookup(gateway, "org", "source", "effect-1")
        assert isinstance(outcome, ds.OutcomeUnknown)
        assert outcome.effect_id == "effect-1"
    else:
        with pytest.raises(ds.OutcomeUnknown) as caught:
            ds.invoke(gateway, "org", "source", "create_invoice", {})
        outcome = caught.value
        assert UUID(outcome.effect_id).version == 7
    assert outcome.effect_id == state.received[0][1]["effect_id"]
    assert outcome.receipt.status is ds.ReceiptStatus.UNKNOWN
    assert isinstance(outcome.__cause__, HTTPError)
    assert outcome.__cause__.code == status
    assert outcome.__cause__.read() == b"proxy rejected the exchange"
    assert len(state.received) == 1


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (500, _error("internal")),
        (500, _error("unknown")),
        (500, _error("data_loss")),
        (401, _error("unauthenticated")),
        (409, _error("already_exists")),
        (409, _error("aborted")),
        (400, _error("out_of_range")),
        (501, _error("unimplemented")),
        (429, _error("resource_exhausted", ErrorInfo(reason="SOME_OTHER_QUOTA"))),
    ],
)
@pytest.mark.parametrize("lookup", [False, True])
def test_unmapped_connect_errors_keep_their_identity(
    connect: tuple[Gateway, State], status: int, payload: dict[str, Any], lookup: bool
) -> None:
    gateway, state = connect
    state.error = status, payload
    with pytest.raises(HTTPError) as caught:
        if lookup:
            ds.lookup(gateway, "org", "source", "effect-1")
        else:
            ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert json.loads(caught.value.read()) == payload
    if not lookup:
        assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert len(state.received) == 1


@pytest.mark.parametrize(
    ("status", "body", "content_type"),
    [
        (429, b"not JSON", "application/json"),
        (500, b"", "application/json"),
        (401, b'{"code":"unauthenticated"}', "text/plain"),
        (500, b'{"code":42}', "application/json"),
        (400, b'{"code":"invalid_argument","details":42}', "application/json"),
        (
            400,
            b'{"code":"invalid_argument","details":[{"type":"google.rpc.BadRequest","value":"not base64!"}]}',
            "application/json",
        ),
        (403, b'{"code":"permission_denied"}', "application/json; charset=latin-1"),
    ],
)
def test_malformed_http_error_is_unknown(
    connect: tuple[Gateway, State], status: int, body: bytes, content_type: str
) -> None:
    gateway, state = connect
    state.raw_error = status, body, content_type
    with pytest.raises(ds.OutcomeUnknown) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert isinstance(caught.value.__cause__, HTTPError)
    assert caught.value.__cause__.read() == body
    assert len(state.received) == 1


@pytest.mark.parametrize("provider_status", ["401", "429", "500"])
def test_provider_status_is_never_inferred_from_metadata(
    connect: tuple[Gateway, State], provider_status: str
) -> None:
    gateway, state = connect
    state.error = (
        400,
        _error(
            "failed_precondition",
            ErrorInfo(
                reason="SOURCE_PROVIDER_REFUSED",
                metadata={"provider_status": provider_status},
            ),
        ),
    )
    with pytest.raises(ds.ProviderRefused) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert caught.value.status is None
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert len(state.received) == 1


def test_deadline_expiring_during_encoding_never_dispatches(
    connect: tuple[Gateway, State], monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway, state = connect
    encode = json.dumps
    monkeypatch.setattr(time, "time", lambda: 10.0)

    def expired_after_encoding(*args: Any, **kwargs: Any) -> str:
        encoded = encode(*args, **kwargs)
        monkeypatch.setattr(time, "time", lambda: 11.0)
        return encoded

    monkeypatch.setattr(json, "dumps", expired_after_encoding)
    with pytest.raises(ds.InputError, match="deadline"):
        ds.invoke(gateway, "org", "source", "create_invoice", {}, deadline=10.5)
    assert not gateway.options
    assert not state.received


@pytest.mark.parametrize(
    ("status", "payload", "expected"),
    [
        (500, {}, HTTPError),
        (429, {}, ds.OutcomeUnknown),
        (403, {}, ds.NotPermitted),
        (500, {"code": "future_code"}, HTTPError),
        (429, {"code": "future_code"}, ds.OutcomeUnknown),
        (
            500,
            {"code": "permission_denied", "message": "declared wire code"},
            ds.NotPermitted,
        ),
        (429, {"code": "internal", "message": "declared wire code"}, HTTPError),
    ],
)
def test_connect_go_lenient_wire_codes(
    connect: tuple[Gateway, State],
    status: int,
    payload: dict[str, Any],
    expected: type[Exception],
) -> None:
    gateway, state = connect
    state.error = status, payload
    with pytest.raises(expected) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert isinstance(caught.value, (HTTPError, ds.DatasourceError))
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert len(state.received) == 1


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            gzip.compress(b'{"code":"permission_denied","message":"host denied"}'),
            ds.NotPermitted,
        ),
        (b"invalid gzip", ds.OutcomeUnknown),
        (gzip.compress(b'{"code":"permission_denied"}')[:12], ds.OutcomeUnknown),
    ],
)
def test_gzip_http_errors_preserve_wire_classification(
    connect: tuple[Gateway, State], body: bytes, expected: type[ds.DatasourceError]
) -> None:
    gateway, state = connect
    state.error_content_encoding = "gzip"
    state.raw_error = (403, body, "application/json")
    with pytest.raises(expected) as caught:
        ds.invoke(gateway, "org", "source", "create_invoice", {})
    assert caught.value.effect_id == state.received[0][1]["effect_id"]
    assert isinstance(caught.value.__cause__, HTTPError)
    assert caught.value.__cause__.read() == body
    assert len(state.received) == 1
