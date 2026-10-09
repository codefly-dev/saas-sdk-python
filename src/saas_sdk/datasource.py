"""Typed, gateway-bound client facade for the saas ``DatasourceService`` — the
connection and call halves of datasource, and the Python twin of
``saas-sdk-go``'s ``datasource`` package.

It is the syntactic-sugar layer over the generated protobuf message types: it
names the Connect procedure and routes every call through the solution runtime's
``Gateway.unary(procedure, request, response_type)`` seam (which owns transport,
auth, and the wire protocol), so a solution connects a GitHub datasource
collection in a few lines::

    from saas_sdk import datasource

    ds = datasource.new(gateway)
    source = ds.add_github_source(
        org_id=org,
        repo="codefly-dev/module-saas-starter",
        paths=["docs"],
        collection="handbook",
        access_token=token,
    )
    ds.sync(org, source.id)

The access token is sent once; the connection side encrypts it and persists only
a secret reference — no read ever returns it.
"""

from __future__ import annotations

import inspect
import json
import math
import secrets
import time
from collections.abc import Mapping, Sequence
from datetime import timezone
from http.client import IncompleteRead
from typing import Any, Protocol, TypeVar, cast
from urllib.error import HTTPError, URLError
from uuid import UUID

from google.protobuf import json_format, message_factory
from google.protobuf.message import DecodeError, Message
from google.protobuf.timestamp_pb2 import Timestamp

from saas_sdk._datasource_errors import map_error, unknown
from saas_sdk._datasource_types import (
    DatasourceError,
    Effect,
    EffectNotFound,
    EffectReused,
    InputError,
    NotPermitted,
    Operation,
    OperationDeclarationRemoved,
    OperationRefused,
    OutcomeUnknown,
    ProviderRefused,
    RateLimited,
    Receipt,
    ReceiptStatus,
    Result,
    UnknownOperation,
)
from saas_sdk._gen import datasource_pb2 as pb

# Re-exported so a consumer names the types this facade returns without importing
# saas_sdk._gen. Same objects, so isinstance and existing imports keep working.
Datasource = pb.Datasource

__all__ = [
    "Client",
    "Datasource",
    "DatasourceError",
    "Effect",
    "EffectNotFound",
    "EffectReused",
    "Gateway",
    "InputError",
    "NotPermitted",
    "Operation",
    "OperationDeclarationRemoved",
    "OperationGateway",
    "OperationRefused",
    "OutcomeUnknown",
    "ProviderRefused",
    "RateLimited",
    "Receipt",
    "ReceiptStatus",
    "Result",
    "UnknownOperation",
    "declare_operations",
    "invoke",
    "list_operations",
    "lookup",
    "new",
]

_M = TypeVar("_M", bound=Message)

_SERVICE = "/saas.accounts.v1.DatasourceService/"


class Gateway(Protocol):
    """Minimal surface this SDK needs from the solution runtime.

    ``solution_runtime.Gateway`` satisfies it as-is: it forwards the caller's
    bearer and owns the Connect transport, so this package stays transport- and
    auth-agnostic.
    """

    def unary(
        self, procedure: str, request: Message, response_type: type[_M]
    ) -> _M: ...


class OperationGateway(Gateway, Protocol):
    """Gateway call options required by the call half.

    The runtime must merge ``headers`` into its request without replacing its
    own Work Context, and apply ``timeout`` in seconds to this one call. It
    must not retry an effect. This is a structural protocol, not an SDK
    dependency for the runtime. The published three-argument runtime gateway
    does not yet implement these options (see README).
    """

    def unary(
        self,
        procedure: str,
        request: Message,
        response_type: type[_M],
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> _M: ...


class Client:
    """Entry point: ``new(gateway).add_github_source(...)``."""

    def __init__(self, gateway: Gateway) -> None:
        self._gateway = gateway

    def add_github_source(
        self,
        *,
        org_id: str,
        repo: str,
        collection: str = "",
        boundary_node_id: str = "",
        access_token: str = "",
        paths: Sequence[str] = (),
        branch: str = "",
        webhook_secret: str = "",
    ) -> Datasource:
        """Register a GitHub repository as a datasource and return the non-secret
        projection the server stored.

        The pulled entries land in exactly one data boundary: ``collection`` is
        a label the host resolves to (or mints as) a collection node, and
        ``boundary_node_id`` names an existing scope node. An empty
        ``access_token`` connects through the deployment's GitHub App instead
        of a pasted token.
        """
        if bool(collection) == bool(boundary_node_id):
            raise ValueError("pass exactly one of collection or boundary_node_id")
        boundary = (
            {"collection_label": collection}
            if collection
            else {"boundary_node_id": boundary_node_id}
        )
        request = pb.AddGitHubSourceRequest(
            org_id=org_id,
            repo=repo,
            paths=list(paths),
            branch=branch,
            access_token=access_token,
            webhook_secret=webhook_secret,
            **boundary,
        )
        response = self._gateway.unary(
            _SERVICE + "AddGitHubSource", request, pb.AddGitHubSourceResponse
        )
        return response.datasource

    def list_sources(self, org_id: str) -> list[Datasource]:
        """Return the org's connected datasources."""
        response = self._gateway.unary(
            _SERVICE + "ListSources",
            pb.ListSourcesRequest(org_id=org_id),
            pb.ListSourcesResponse,
        )
        return list(response.datasources)

    def sync(self, org_id: str, id: str) -> str:
        """Mark a source for ingestion and return the durable jobs-inbox id of
        the enqueued request."""
        response = self._gateway.unary(
            _SERVICE + "SyncSource",
            pb.SyncSourceRequest(org_id=org_id, id=id),
            pb.SyncSourceResponse,
        )
        return response.job_id

    def invoke(
        self,
        org_id: str,
        source_id: str,
        operation: str,
        input: Mapping[str, Any],
        *,
        effect_id: str | None = None,
        deadline: float | None = None,
    ) -> Result:
        """Invoke once; ``deadline`` is an absolute Unix timestamp in seconds.

        Persist a caller-chosen effect ID before a mutation when recovery must
        survive a process crash. If this call loses its reply, OutcomeUnknown
        retains even a minted ID. Lookup that ID; never retry with a new one.
        """
        if effect_id is None:
            effect_id = _uuid7()
        _validate_effect_id(effect_id)
        # The Runnable envelope carries one JSON object as text. Keeping it
        # out of Struct also preserves integers beyond the double range.
        try:
            if not isinstance(input, Mapping):
                raise TypeError("input must be a JSON object")
            input_json = json.dumps(dict(input), allow_nan=False, separators=(",", ":"))
        except (ValueError, TypeError) as error:
            raise InputError(str(error)) from error
        # Preparing the request consumes the deadline budget.
        timeout = None
        if deadline is not None:
            timeout = deadline - time.time()
            if not math.isfinite(deadline) or timeout <= 0:
                raise InputError("deadline must be a finite future Unix timestamp")
        try:
            response = _rpc(
                self._gateway,
                "InvokeSourceOperation",
                {
                    "org_id": org_id,
                    "source_id": source_id,
                    "operation": operation,
                    "input_json": input_json,
                    "effect_id": effect_id,
                },
                effect_id=effect_id,
                headers={"x-codefly-effect-id": effect_id},
                timeout=timeout,
            )
        except (
            TimeoutError,
            ConnectionError,
            IncompleteRead,
            DecodeError,
            URLError,
        ) as error:
            # HTTPError is a URLError too. _rpc already classifies HTTP replies;
            # only an unmapped, recognized Connect error can remain here.
            if isinstance(error, HTTPError):
                raise
            raise unknown(effect_id, str(error)) from error
        try:
            receipt = _receipt(response["receipt"])
            output = _json_object(response.get("output_json", ""))
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise unknown(
                effect_id, "host returned a missing or invalid operation response"
            ) from error
        if receipt.effect_id != effect_id:
            raise unknown(
                effect_id, "host returned a receipt for a different effect ID"
            )
        if _is_unknown(receipt):
            raise OutcomeUnknown("host has not resolved the effect", receipt=receipt)
        return Result(output=output, receipt=receipt)

    def lookup(
        self, org_id: str, source_id: str, effect_id: str
    ) -> Receipt | OutcomeUnknown | EffectNotFound | OperationDeclarationRemoved:
        """Read a receipt once. Unknown is a value, never raised here.

        org_id/source_id retain the Go facade's signature; the wire selector is
        only effect_id. The host resolves its binding under the gateway's tenant.
        """
        _validate_effect_id(effect_id)
        try:
            response = _rpc(
                self._gateway,
                "LookupInvokeSourceOperation",
                {"effect_id": effect_id},
                effect_id=effect_id,
                lookup=True,
            )
        except (OutcomeUnknown, EffectNotFound, OperationDeclarationRemoved) as outcome:
            return outcome
        try:
            receipt = _receipt(response["receipt"])
            if receipt.effect_id != effect_id:
                raise ValueError("host returned a receipt for a different effect ID")
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            failure = DatasourceError(
                "host returned a missing or invalid lookup receipt"
            )
            failure.effect_id = effect_id
            raise failure from error
        if _is_unknown(receipt):
            return OutcomeUnknown("host has not resolved the effect", receipt=receipt)
        return receipt

    def declare_operations(
        self, org_id: str, source_id: str, operations: list[Operation]
    ) -> None:
        """Replace the host's declarations atomically (host-admin permission)."""
        _rpc(
            self._gateway,
            "DeclareSourceOperations",
            {
                "org_id": org_id,
                "source_id": source_id,
                "operations": [
                    _operation_fields(operation) for operation in operations
                ],
            },
        )

    def list_operations(self, org_id: str, source_id: str) -> list[Operation]:
        """Read the host's admitted declaration set without caching it."""
        response = _rpc(
            self._gateway,
            "ListSourceOperations",
            {"org_id": org_id, "source_id": source_id},
        )
        return [_operation(value) for value in response.get("operations", [])]


def new(gateway: Gateway) -> Client:
    """Bind the datasource SDK to a solution runtime gateway."""
    return Client(gateway)


def invoke(
    gw: OperationGateway,
    org_id: str,
    source_id: str,
    operation: str,
    input: Mapping[str, Any],
    *,
    effect_id: str | None = None,
    deadline: float | None = None,
) -> Result:
    """Call the same facade as ``new(gw).invoke(...)``."""
    return new(gw).invoke(
        org_id, source_id, operation, input, effect_id=effect_id, deadline=deadline
    )


def lookup(
    gw: Gateway, org_id: str, source_id: str, effect_id: str
) -> Receipt | OutcomeUnknown | EffectNotFound | OperationDeclarationRemoved:
    return new(gw).lookup(org_id, source_id, effect_id)


def declare_operations(
    gw: Gateway, org_id: str, source_id: str, operations: list[Operation]
) -> None:
    new(gw).declare_operations(org_id, source_id, operations)


def list_operations(gw: Gateway, org_id: str, source_id: str) -> list[Operation]:
    return new(gw).list_operations(org_id, source_id)


def _uuid7() -> str:
    # RFC 9562: 48 timestamp bits, version 7, 12 random bits, variant 10,
    # 62 random bits. Python 3.10/3.12 do not supply uuid.uuid7.
    random = secrets.randbits(74)
    value = ((time.time_ns() // 1_000_000) << 80) | (7 << 76)
    value |= (random >> 62) << 64
    value |= (2 << 62) | (random & ((1 << 62) - 1))
    return str(UUID(int=value))


def _rpc(
    gateway: Gateway,
    method: str,
    fields: dict[str, Any],
    *,
    effect_id: str | None = None,
    lookup: bool = False,
    headers: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    # Resolve both message types from the generated method descriptor. The
    # host owns these types; there is no guessed wire schema or fallback here.
    service = pb.DESCRIPTOR.services_by_name["DatasourceService"]
    descriptor = service.methods_by_name[method]
    request_type = message_factory.GetMessageClass(descriptor.input_type)
    response_type = message_factory.GetMessageClass(descriptor.output_type)
    try:
        request = json_format.ParseDict(fields, request_type())
    except json_format.ParseError as error:
        raise InputError(str(error)) from error
    if headers is not None or timeout is not None:
        try:
            inspect.signature(gateway.unary).bind(
                _SERVICE + method,
                request,
                response_type,
                headers=headers,
                timeout=timeout,
            )
        except (TypeError, ValueError) as error:
            raise TypeError(
                "invoke requires OperationGateway.unary with headers and timeout keyword options; "
                "upgrade the runtime gateway before calling connected sources"
            ) from error
    try:
        try:
            if headers is None and timeout is None:
                response = gateway.unary(_SERVICE + method, request, response_type)
            else:
                response = cast(OperationGateway, gateway).unary(
                    _SERVICE + method,
                    request,
                    response_type,
                    headers=headers,
                    timeout=timeout,
                )
        except HTTPError as error:
            mapped = map_error(error, effect_id=effect_id, lookup=lookup)
            if mapped is None:
                if effect_id is not None:
                    raise unknown(effect_id, str(error)) from error
                raise
            if mapped is error:
                raise
            raise mapped from error
        return json_format.MessageToDict(response, preserving_proto_field_name=True)
    except Exception as error:
        # Go returns Result alongside every post-dispatch error. Python errors
        # retain the same recovery identity, including raw gateway exceptions.
        if (
            effect_id is not None
            and not lookup
            and getattr(error, "effect_id", None) is None
        ):
            vars(error).update(
                effect_id=effect_id, receipt=Receipt(effect_id, ReceiptStatus.UNKNOWN)
            )
        raise


def _receipt(value: dict[str, Any]) -> Receipt:
    committed_at = None
    if value.get("committed_at"):
        timestamp = Timestamp()
        timestamp.FromJsonString(value["committed_at"])
        committed_at = timestamp.ToDatetime(tzinfo=timezone.utc)
    if not isinstance(value.get("status"), str):
        raise TypeError("host returned an unsupported receipt status")
    statuses = {"committed": ReceiptStatus.COMMITTED, "unknown": ReceiptStatus.UNKNOWN}
    if value["status"] not in statuses:
        raise ValueError("host returned an unsupported receipt status")
    status = statuses[value["status"]]
    output = _json_object(value.get("output_json", ""))
    return Receipt(
        effect_id=value["effect_id"],
        status=status,
        committed_at=committed_at,
        provider_status=value.get("provider_status"),
        output=output if status is ReceiptStatus.COMMITTED else None,
    )


def _is_unknown(receipt: Receipt) -> bool:
    return receipt.status is ReceiptStatus.UNKNOWN


def _json_object(value: str) -> dict[str, Any]:
    def reject_constant(constant: str) -> None:
        raise ValueError(f"invalid JSON constant: {constant}")

    decoded = json.loads(value, parse_constant=reject_constant)
    if not isinstance(decoded, dict):
        raise TypeError("host output must contain exactly one JSON object")
    return decoded


def _operation_fields(operation: Operation) -> dict[str, Any]:
    effects = {Effect.READ_ONLY: "EFFECT_READ_ONLY", Effect.MUTATION: "EFFECT_MUTATION"}
    if not isinstance(operation.effect, Effect):
        raise InputError("invalid operation effect")
    effect = effects[operation.effect]
    return {
        "name": operation.name,
        "description": operation.description,
        "method": operation.method,
        "path": operation.path,
        "query": operation.query,
        "input_schema": operation.input,
        "output_schema": operation.output,
        "effect": effect,
        "max_output_bytes": operation.max_output_bytes,
    }


def _operation(value: dict[str, Any]) -> Operation:
    effect = {
        "EFFECT_READ_ONLY": Effect.READ_ONLY,
        "EFFECT_MUTATION": Effect.MUTATION,
    }.get(value.get("effect", ""))
    if effect is None:
        raise DatasourceError("host returned an unsupported operation effect")
    return Operation(
        name=value.get("name", ""),
        description=value.get("description", ""),
        digest=value.get("digest", ""),
        method=value.get("method", ""),
        path=value.get("path", ""),
        query=value.get("query", []),
        input=value.get("input_schema", {}),
        output=value.get("output_schema", {}),
        effect=effect,
        max_output_bytes=int(value.get("max_output_bytes", 0)),
    )


def _validate_effect_id(effect_id: str) -> None:
    try:
        encoded = effect_id.encode("utf-8")
    except UnicodeEncodeError as error:
        raise InputError("effect_id must be valid UTF-8") from error
    # HTTP transports trim edge spaces, which would make header and field differ.
    if (
        not 1 <= len(encoded) <= 128
        or effect_id.startswith(" ")
        or effect_id.endswith(" ")
        or any(byte < 32 or byte == 127 for byte in encoded)
    ):
        raise InputError(
            "effect_id must be 1–128 UTF-8 bytes without HTTP controls or edge spaces"
        )
