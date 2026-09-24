"""Typed, gateway-bound client facade for the saas ``AuditService`` — reading an
organization's append-only audit trail as the signed-in person.

Like :mod:`saas_sdk.datasource`, it names the Connect procedure and routes every
call through the solution runtime's ``Gateway.unary(procedure, request,
response_type)`` seam, which owns transport, auth and the wire protocol::

    from saas_sdk import audit

    log = audit.new(gateway)
    page = log.query(org_id, event_type="example.item.created", page_size=20)
    for event in page.events:
        ...
    counts = log.aggregate(org_id, group_bys=["event_type"])
    types = log.list_event_types()

All three RPCs are authenticated public gateway calls made as the signed-in
person: each needs ``audit:read``, and ``query`` / ``aggregate`` additionally need
membership of ``org_id``. A refusal of the caller — Connect ``unauthenticated`` or
``permission_denied`` — raises :class:`AuditDenied`; every other failure is the
gateway's own error, unchanged.
"""

from __future__ import annotations

import json
import urllib.error
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol, TypeVar

from google.protobuf.timestamp_pb2 import Timestamp

from saas_sdk._gen import audit_pb2 as pb

# Re-exported so a consumer names the types this facade takes and returns without
# importing saas_sdk._gen. Same objects, so isinstance and existing imports work.
AuditEvent = pb.AuditEvent
AuditEventType = pb.AuditEventType
AuditMetric = pb.AuditMetric
AuditDerivedMetric = pb.AuditDerivedMetric
AuditAggregateBucket = pb.AuditAggregateBucket
QueryAuditLogResponse = pb.QueryAuditLogResponse
AggregateAuditLogResponse = pb.AggregateAuditLogResponse

__all__ = [
    "AggregateAuditLogResponse",
    "AuditAggregateBucket",
    "AuditDenied",
    "AuditDerivedMetric",
    "AuditEvent",
    "AuditEventType",
    "AuditMetric",
    "Client",
    "DEFAULT_PAGE_SIZE",
    "Gateway",
    "PERMISSION_DENIED",
    "QueryAuditLogResponse",
    "UNAUTHENTICATED",
    "new",
]

_M = TypeVar("_M")

_SERVICE = "/saas.accounts.v1.AuditService/"

# The Connect codes of a refusal, and the HTTP status Connect pairs each with.
UNAUTHENTICATED = "unauthenticated"
PERMISSION_DENIED = "permission_denied"
_REFUSALS = {401: UNAUTHENTICATED, 403: PERMISSION_DENIED}
_MAX_ERROR_BYTES = 64 * 1024

# QueryAuditLogRequest.page_size is validated as 0 < page_size <= 100 on the
# server, so an unset (zero) size is rejected rather than defaulted. 50 is the
# size the host's store falls back to.
DEFAULT_PAGE_SIZE = 50


class AuditDenied(Exception):
    """The accounts service refused the caller: Connect ``unauthenticated`` (no
    valid signed-in person) or ``permission_denied`` (the person lacks
    ``audit:read`` or membership of the organization).

    Distinct from a transport or server failure, which surfaces as the gateway's
    own error, so a solution can answer "sign in" / "not allowed" to its user
    instead of "try again later". ``code`` is :data:`UNAUTHENTICATED` or
    :data:`PERMISSION_DENIED`; ``procedure`` is the RPC method name.
    """

    def __init__(self, procedure: str, code: str) -> None:
        self.procedure = procedure
        self.code = code
        super().__init__(f"{procedure}: {code}")


class Gateway(Protocol):
    """Minimal surface this SDK needs from the solution runtime.

    ``solution_runtime.Gateway`` satisfies it as-is: it is bound to the caller's
    bearer and owns the Connect transport, so every audit read is made as the
    signed-in person and this package stays transport- and auth-agnostic.
    """

    def unary(self, procedure: str, request, response_type: type[_M]) -> _M: ...


class Client:
    """Entry point: ``new(gateway).query(org_id, ...)``."""

    def __init__(self, gateway: Gateway) -> None:
        self._gateway = gateway

    def query(
        self,
        org_id: str,
        *,
        actor_id: str = "",
        event_type: str = "",
        category: str = "",
        resource: str = "",
        resource_id: str = "",
        payload_contains: Mapping[str, str] | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        page_token: str = "",
    ) -> QueryAuditLogResponse:
        """Return one page of the organization's audit events, newest first.

        Empty filters match everything. ``payload_contains`` matches events whose
        payload contains every given key/value. ``from_`` / ``to`` must be
        timezone-aware. Pass the response's ``next_page_token`` back as
        ``page_token`` for the next page; it is empty on the last page.
        """
        request = pb.QueryAuditLogRequest(
            org_id=org_id,
            actor_id=actor_id,
            event_type=event_type,
            category=category,
            resource=resource,
            resource_id=resource_id,
            payload_contains=dict(payload_contains or {}),
            page_size=page_size,
            page_token=page_token,
            **_window(from_, to),
        )
        return self._call("QueryAuditLog", request, pb.QueryAuditLogResponse)

    def aggregate(
        self,
        org_id: str,
        *,
        actor_id: str = "",
        event_type: str = "",
        category: str = "",
        resource: str = "",
        from_: datetime | None = None,
        to: datetime | None = None,
        group_bys: Sequence[str] = (),
        bucket: str = "",
        metrics: Sequence[AuditMetric] = (),
        derived: Sequence[AuditDerivedMetric] = (),
    ) -> AggregateAuditLogResponse:
        """Group the organization's audit events and compute metrics per group.

        ``group_bys`` entries are ``event_type``, ``category``, ``actor``, ``time``
        or ``payload:<key>`` (server default: ``event_type``); ``bucket`` sizes a
        ``time`` dimension (``day`` / ``week`` / ``month``). Empty ``metrics``
        means a single count per group. The whole response is returned, not just
        its buckets, so fields the server adds to it stay reachable.
        """
        request = pb.AggregateAuditLogRequest(
            org_id=org_id,
            actor_id=actor_id,
            event_type=event_type,
            category=category,
            resource=resource,
            group_bys=list(group_bys),
            bucket=bucket,
            metrics=list(metrics),
            derived=list(derived),
            **_window(from_, to),
        )
        return self._call("AggregateAuditLog", request, pb.AggregateAuditLogResponse)

    def list_event_types(self) -> list[AuditEventType]:
        """Return the registered audit event types."""
        response = self._call(
            "ListAuditEventTypes", pb.ListAuditEventTypesRequest(), pb.ListAuditEventTypesResponse
        )
        return list(response.types)

    def _call(self, method: str, request, response_type: type[_M]) -> _M:
        try:
            return self._gateway.unary(_SERVICE + method, request, response_type)
        except AuditDenied:
            # A gateway that already speaks this error must not be double-wrapped.
            raise
        except urllib.error.HTTPError as err:
            code = _refusal_code(err)
            if code is None:
                raise
            raise AuditDenied(method, code) from err


def _refusal_code(error: urllib.error.HTTPError) -> str | None:
    """The Connect code of a refusal carried by ``error``, else ``None``.

    ``solution_runtime.Gateway`` raises urllib's ``HTTPError`` for a Connect error
    response: an HTTP status plus a JSON body naming the code. Only the coherent
    pairs 401/``unauthenticated`` and 403/``permission_denied`` are refusals; any
    other status, or a body that does not name the matching code, is left as the
    gateway's error. Another gateway can raise :class:`AuditDenied` itself.
    """
    expected = _REFUSALS.get(error.code)
    if expected is None:
        return None
    try:
        body = json.loads(error.read(_MAX_ERROR_BYTES))
    except (OSError, ValueError):
        return None
    if isinstance(body, dict) and body.get("code") == expected:
        return expected
    return None


def _window(from_: datetime | None, to: datetime | None) -> dict[str, Timestamp]:
    # ``from`` is a Python keyword, so the time window is passed to the message
    # constructor as keyword arguments, and only when set.
    window = {}
    for field, value in (("from", from_), ("to", to)):
        if value is not None:
            window[field] = _timestamp(field, value)
    return window


def _timestamp(field: str, value: datetime) -> Timestamp:
    if value.tzinfo is None or value.utcoffset() is None:
        # Timestamp.FromDatetime reads a naive datetime as UTC, which silently
        # shifts a local wall-clock time; make the caller say which zone it means.
        raise ValueError(f"{field} must be a timezone-aware datetime")
    timestamp = Timestamp()
    timestamp.FromDatetime(value)
    return timestamp


def new(gateway: Gateway) -> Client:
    """Bind the audit SDK to a solution runtime gateway."""
    return Client(gateway)
