"""Callee-side verification of a signed Codefly **Work Context** — the Python
twin of ``sdk-go``'s ``work_context.go`` (v0.1.65), which owns the wire format.

A Work Context is the capability accounts mints when a user (the *owner*)
delegates a Task to an agent: it carries the owner, the tenant, the task and
session lineage, the delegated scopes, and the actor chain, and it travels in
the ``x-codefly-work-context`` header (HTTP and gRPC metadata alike). It is
**not** a JWT: the token is two base64url segments, ``payload.signature``, where
the payload is one fixed snake_case JSON layout and the signature is Ed25519
over the raw payload bytes.

This module verifies; it never mints. A callee that receives the header does::

    from saas_sdk import work_context as wc

    verifier = wc.WorkContextVerifier({kid: public_key_bytes})
    ctx = verifier.verify(
        wc.from_headers(request.headers),
        wc.WorkContextExpectations(issuer="saas-starter", audience="my-service"),
    )
    ctx.require_scope("robin:tasks", "execute")   # raises WorkContextDenied

Rotation-aware key discovery from the accounts JWKS lives in
:mod:`saas_sdk.jwks`; a FastAPI dependency in :mod:`saas_sdk.work_context_fastapi`.

Every structural bound, the validation order, the time checks, the expectation
matching, and the scope semantics below mirror sdk-go line for line so a token
Go accepts, Python accepts, and vice versa — the Go golden fixture under
``tests/fixtures`` pins that. Two deliberate places where Python is *stricter*
(never looser) are called out inline.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

__all__ = [
    "ACCOUNTS_ISSUER",
    "CLOCK_SKEW_SECONDS",
    "DEFAULT_TTL_SECONDS",
    "HEADER_NAME",
    "MAX_ACTOR_DEPTH",
    "MAX_TOKEN_BYTES",
    "MAX_TTL_SECONDS",
    "REPLAY_IDEMPOTENT",
    "REPLAY_SINGLE_USE",
    "WORK_CONTEXT_ALGORITHM",
    "WORK_CONTEXT_TYPE",
    "WorkActor",
    "WorkContext",
    "WorkContextDenied",
    "WorkContextError",
    "WorkContextExpectations",
    "WorkContextVerifier",
    "WorkScope",
    "HeaderSource",
    "attach",
    "from_headers",
    "has_scope",
    "parse_token",
    "require_scope",
    "validate_token_shape",
]

# The only carrier for a signed Work Context, on HTTP and gRPC metadata alike.
HEADER_NAME = "x-codefly-work-context"

WORK_CONTEXT_TYPE = "codefly.work-context/v1"
WORK_CONTEXT_ALGORITHM = "Ed25519"

REPLAY_IDEMPOTENT = "idempotent"
REPLAY_SINGLE_USE = "single-use"

MAX_ACTOR_DEPTH = 16
MAX_TOKEN_BYTES = 32 * 1024

# Minter-side lifetimes, here only because the verifier enforces the cap.
DEFAULT_TTL_SECONDS = 5 * 60
MAX_TTL_SECONDS = 15 * 60
# Both the default and the largest skew a verifier may be configured with.
CLOCK_SKEW_SECONDS = 60

# What the composed accounts service puts in ``issuer`` when it mints
# (``accounts/code/work.go``). sdk-go itself has no default; a callee should
# pin whatever its accounts deployment actually issues.
ACCOUNTS_ISSUER = "saas-starter"

_MAX_ID_BYTES = 512
_MAX_KIND_BYTES = 128
_MAX_SCOPES = 64
_MAX_SCOPE_ENTRIES = 256
_SIGNATURE_SIZE = 64
_PUBLIC_KEY_SIZE = 32
_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1
_UINT64_MAX = 2**64 - 1
_UINT64_DECIMAL = re.compile(r"[0-9]+")


class WorkContextError(ValueError):
    """The token is not a valid, trusted Work Context (sdk-go's
    ``ErrWorkContextInvalid``): malformed, forged, expired, out of bounds, or
    not matching the callee's expectations. Always fail closed on it."""


class WorkContextDenied(PermissionError):
    """A *valid* Work Context does not grant the required scope (sdk-go's
    ``ErrWorkContextDenied``). Deliberately not a :class:`WorkContextError`
    subclass so a 401 (untrusted) and a 403 (trusted but denied) stay distinct."""


@dataclass(frozen=True)
class WorkScope:
    """One structured capability. Empty ``resource_ids`` means every resource of
    ``resource_kind``; both tuples are sorted and unique on a valid token."""

    resource_kind: str
    actions: tuple[str, ...] = ()
    resource_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkActor:
    """One verified delegated actor; ``granted_scopes`` must attenuate the hop
    before it."""

    principal_id: str
    principal_kind: str
    delegation_id: str
    granted_scopes: tuple[WorkScope, ...] = ()


@dataclass(frozen=True)
class WorkContext:
    """The verified claims (``codefly.base.v0.WorkContextV1``). Task identity is
    the tuple ``(tenant_id, owner_principal_id, task_id)``."""

    typ: str
    algorithm: str
    key_id: str
    issuer: str
    audience: str
    not_before_unix: int
    issued_at_unix: int
    expires_at_unix: int
    nonce: str
    authorization_revision: int
    replay_policy: str
    tenant_id: str
    owner_principal_id: str
    task_id: str
    session_id: str
    parent_session_id: str | None = None
    authority_scopes: tuple[WorkScope, ...] = ()
    actor_chain: tuple[WorkActor, ...] = ()
    attribution_team_ids: tuple[str, ...] = ()
    workspace_id: str | None = None
    project_id: str | None = None

    @property
    def current_actor(self) -> WorkActor | None:
        """The last actor in the chain, or ``None`` on a direct owner call."""
        return self.actor_chain[-1] if self.actor_chain else None

    @property
    def effective_scopes(self) -> tuple[WorkScope, ...]:
        """What the current caller may do: the final actor's granted scopes when
        actors are present, otherwise the owner's authority scopes."""
        actor = self.current_actor
        return actor.granted_scopes if actor is not None else self.authority_scopes

    def has_scope(
        self,
        resource_kind: str,
        action: str,
        resource_id: str | None = None,
        *,
        require_explicit_resource: bool = False,
    ) -> bool:
        """See :func:`has_scope`."""
        return has_scope(
            self,
            resource_kind,
            action,
            resource_id,
            require_explicit_resource=require_explicit_resource,
        )

    def require_scope(
        self,
        resource_kind: str,
        action: str,
        resource_id: str | None = None,
        *,
        require_explicit_resource: bool = False,
    ) -> None:
        """See :func:`require_scope`."""
        require_scope(
            self,
            resource_kind,
            action,
            resource_id,
            require_explicit_resource=require_explicit_resource,
        )

    def to_dict(self) -> dict[str, Any]:
        """The payload as sdk-go lays it out on the wire (field order included;
        ``authorization_revision`` as a decimal string, optional ids omitted)."""
        payload: dict[str, Any] = {
            "typ": self.typ,
            "algorithm": self.algorithm,
            "key_id": self.key_id,
            "issuer": self.issuer,
            "audience": self.audience,
            "not_before_unix": self.not_before_unix,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
            "nonce": self.nonce,
            "authorization_revision": str(self.authorization_revision),
            "replay_policy": self.replay_policy,
            "tenant_id": self.tenant_id,
            "owner_principal_id": self.owner_principal_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
        }
        if self.parent_session_id is not None:
            payload["parent_session_id"] = self.parent_session_id
        payload["authority_scopes"] = [_scope_to_dict(s) for s in self.authority_scopes]
        payload["actor_chain"] = [
            {
                "principal_id": a.principal_id,
                "principal_kind": a.principal_kind,
                "delegation_id": a.delegation_id,
                "granted_scopes": [_scope_to_dict(s) for s in a.granted_scopes],
            }
            for a in self.actor_chain
        ]
        payload["attribution_team_ids"] = list(self.attribution_team_ids)
        if self.workspace_id is not None:
            payload["workspace_id"] = self.workspace_id
        if self.project_id is not None:
            payload["project_id"] = self.project_id
        return payload


@dataclass(frozen=True)
class WorkContextExpectations:
    """What the callee insists on. Each string is checked only when non-empty;
    ``parent_session_id`` / ``authorization_revision`` only when not ``None``
    — the same "unset means don't care" rule as sdk-go."""

    issuer: str = ""
    audience: str = ""
    tenant_id: str = ""
    owner_principal_id: str = ""
    task_id: str = ""
    session_id: str = ""
    parent_session_id: str | None = None
    authorization_revision: int | None = None


# --------------------------------------------------------------------------- #
# Wire shape
# --------------------------------------------------------------------------- #


def validate_token_shape(encoded: str) -> str:
    """Bounded two-segment shape only (``ParseWorkContextToken``). Establishes
    no trust; returns the token for chaining."""
    if not isinstance(encoded, str) or encoded == "":
        raise WorkContextError("empty token")
    if len(encoded.encode("utf-8")) > MAX_TOKEN_BYTES:
        raise WorkContextError(f"token exceeds {MAX_TOKEN_BYTES} bytes")
    if encoded.count(".") != 1:
        raise WorkContextError("token must have exactly two segments")
    return encoded


def parse_token(encoded: str) -> tuple[bytes, bytes]:
    """Split and decode ``payload.signature``. Each segment must be canonical
    unpadded base64url (re-encoding reproduces it byte for byte) and the
    signature exactly 64 bytes. No trust is established."""
    validate_token_shape(encoded)
    payload_segment, signature_segment = encoded.split(".", 1)
    payload = _decode_canonical(payload_segment, "payload")
    signature = _decode_canonical(signature_segment, "signature")
    if len(signature) != _SIGNATURE_SIZE:
        raise WorkContextError(f"signature must be {_SIGNATURE_SIZE} bytes")
    return payload, signature


def _decode_canonical(segment: str, name: str) -> bytes:
    try:
        raw = segment.encode("ascii")
        decoded = base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise WorkContextError(f"{name} base64: {exc}") from exc
    if base64.urlsafe_b64encode(decoded).rstrip(b"=") != raw:
        raise WorkContextError(f"{name} is not canonical base64url")
    return decoded


HeaderSource = Mapping[str, Any] | Iterable[tuple[Any, Any]]


def from_headers(headers: HeaderSource) -> str:
    """Extract the opaque token from a request's headers or gRPC metadata
    (``WorkContextFromHeaders``). Shape-checked only — verify it before using
    any claim.

    Accepts a mapping (multi-value ones such as Starlette's ``Headers`` or
    ``http.client.HTTPMessage`` are read through ``items()``, so every value is
    seen) or an iterable of ``(name, value)`` pairs — ASGI raw headers, gRPC
    ``invocation_metadata()``. Names match case-insensitively; bytes are fine.
    Exactly one carrier value must be present: a duplicated header is rejected
    rather than resolved first-wins, so a proxy-appended or smuggled second
    value can never shadow the one the caller attached.
    """
    if headers is None:
        raise WorkContextError("missing HTTP headers")
    # Duck-typed on purpose: http.client.HTTPMessage and friends are not
    # registered as collections.abc.Mapping but do expose every pair via items().
    pairs = headers.items() if hasattr(headers, "items") else headers
    try:
        values = [_text(value) for name, value in pairs if _text(name).lower() == HEADER_NAME]
    except (TypeError, ValueError) as exc:
        raise WorkContextError(f"unreadable headers: {exc}") from exc
    if not values:
        raise WorkContextError("missing Work Context header")
    if len(values) > 1:
        raise WorkContextError("duplicated Work Context header")
    return validate_token_shape(values[0])


def _text(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("latin-1")
    if isinstance(value, str):
        return value
    raise TypeError(f"header name/value must be str or bytes, not {type(value).__name__}")


def attach(headers: MutableMapping[str, str], encoded: str) -> None:
    """Install a token on outgoing headers without naming the carrier in
    product code (``AttachWorkContext``)."""
    headers[HEADER_NAME] = validate_token_shape(encoded)


# --------------------------------------------------------------------------- #
# Verifier
# --------------------------------------------------------------------------- #


class WorkContextVerifier:
    """Verifies Work Contexts against a fixed ``{kid: 32-byte Ed25519 public
    key}`` map. For keys discovered from the accounts JWKS, wrap it with
    :class:`saas_sdk.jwks.JWKSKeySource` instead.

    ``clock_skew`` is in seconds and may be at most :data:`CLOCK_SKEW_SECONDS`;
    ``now`` returns unix seconds (a float) or an aware ``datetime``. Unlike
    sdk-go, an explicit ``0`` skew is honored (Go's zero value means "default").
    """

    def __init__(
        self,
        public_keys: Mapping[str, bytes],
        *,
        clock_skew: float | None = None,
        now: Callable[[], float | datetime] = time.time,
    ) -> None:
        if not public_keys:
            raise WorkContextError("no public verification keys")
        keys: dict[str, Ed25519PublicKey] = {}
        for key_id, raw in public_keys.items():
            _validate_bounded("key_id", key_id, _MAX_KIND_BYTES, required=True)
            if not isinstance(raw, (bytes, bytearray)) or len(raw) != _PUBLIC_KEY_SIZE:
                raise WorkContextError(f"public key {key_id!r} must be {_PUBLIC_KEY_SIZE} bytes")
            try:
                keys[key_id] = Ed25519PublicKey.from_public_bytes(bytes(raw))
            except ValueError as exc:
                raise WorkContextError(f"public key {key_id!r}: {exc}") from exc
        if clock_skew is None:
            clock_skew = CLOCK_SKEW_SECONDS
        if clock_skew < 0 or clock_skew > CLOCK_SKEW_SECONDS:
            raise WorkContextError(f"clock skew must be between zero and {CLOCK_SKEW_SECONDS}s")
        self._keys = keys
        self._clock_skew = float(clock_skew)
        self._now = now

    @property
    def key_ids(self) -> frozenset[str]:
        return frozenset(self._keys)

    def verify(
        self, encoded: str, expectations: WorkContextExpectations | None = None
    ) -> WorkContext:
        """Decode → pick the key by ``key_id`` → Ed25519-verify the raw payload →
        unmarshal strictly → structural bounds → time window → expectations.
        Exactly sdk-go's ``Verify`` order; the first failure raises
        :class:`WorkContextError`."""
        payload, signature = parse_token(encoded)
        key_id = _probe_key_id(payload)
        public_key = self._keys.get(key_id)
        if public_key is None:
            raise WorkContextError(f"unknown key id {key_id!r}")
        try:
            public_key.verify(signature, payload)
        except InvalidSignature as exc:
            raise WorkContextError("signature verification failed") from exc
        context = _unmarshal(payload)
        _validate(context)
        self._validate_time(context)
        _match(context, expectations or WorkContextExpectations())
        return context

    def _validate_time(self, context: WorkContext) -> None:
        now = _unix(self._now())
        skew = self._clock_skew
        if now < context.not_before_unix - skew:
            raise WorkContextError("token is not active yet")
        if context.issued_at_unix > now + skew:
            raise WorkContextError("token was issued in the future")
        if now > context.expires_at_unix + skew:
            raise WorkContextError("token expired")


def _unix(value: float | datetime) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    return float(value)


def _probe_key_id(payload: bytes) -> str:
    """Read only ``key_id`` before any trust exists (unknown fields tolerated,
    as in Go's probe); everything else waits for the signature check."""
    try:
        probe = json.loads(payload)
    except (UnicodeDecodeError, ValueError) as exc:
        raise WorkContextError(f"decode key id: {exc}") from exc
    if probe is None:
        return ""
    if not isinstance(probe, dict):
        raise WorkContextError("decode key id: payload is not a JSON object")
    key_id = probe.get("key_id", "")
    if key_id is None:
        return ""
    if not isinstance(key_id, str):
        raise WorkContextError("decode key id: key_id must be a string")
    return key_id


def _match(context: WorkContext, expected: WorkContextExpectations) -> None:
    for name, got, want in (
        ("issuer", context.issuer, expected.issuer),
        ("audience", context.audience, expected.audience),
        ("tenant", context.tenant_id, expected.tenant_id),
        ("owner", context.owner_principal_id, expected.owner_principal_id),
        ("task", context.task_id, expected.task_id),
        ("session", context.session_id, expected.session_id),
    ):
        if want != "" and got != want:
            raise WorkContextError(f"{name} mismatch")
    if (
        expected.parent_session_id is not None
        and (context.parent_session_id or "") != expected.parent_session_id
    ):
        raise WorkContextError("parent session mismatch")
    if (
        expected.authorization_revision is not None
        and context.authorization_revision != expected.authorization_revision
    ):
        raise WorkContextError("authorization revision mismatch")


# --------------------------------------------------------------------------- #
# Scopes
# --------------------------------------------------------------------------- #


def require_scope(
    context: WorkContext,
    resource_kind: str,
    action: str,
    resource_id: str | None = None,
    *,
    require_explicit_resource: bool = False,
) -> None:
    """Demand one exact capability of the current actor's effective scope
    (``RequireWorkContextScope``).

    A scope entry matches when its ``resource_kind`` and ``actions`` cover the
    request and either its ``resource_ids`` is empty (a wildcard over the kind —
    unless ``require_explicit_resource``) or it lists ``resource_id``. An
    explicit ``resource_ids`` set is never ignored: asking for the kind with no
    ``resource_id`` is denied by such an entry.

    Call only after :meth:`WorkContextVerifier.verify`. The claims are
    re-validated structurally so a hand-built or mutated context fails closed
    with :class:`WorkContextError`; a valid one that lacks the capability raises
    :class:`WorkContextDenied`.
    """
    _validate(context)
    _validate_bounded("required resource_kind", resource_kind, _MAX_KIND_BYTES, required=True)
    _validate_bounded("required action", action, _MAX_KIND_BYTES, required=True)
    _validate_bounded(
        "required resource_id",
        resource_id or "",
        _MAX_ID_BYTES,
        required=require_explicit_resource,
    )
    wanted = resource_id or ""
    for scope in context.effective_scopes:
        if scope.resource_kind != resource_kind or action not in scope.actions:
            continue
        if not scope.resource_ids and not require_explicit_resource:
            return
        if wanted != "" and wanted in scope.resource_ids:
            return
    raise WorkContextDenied(f"{resource_kind}:{action}:{wanted}")


def has_scope(
    context: WorkContext,
    resource_kind: str,
    action: str,
    resource_id: str | None = None,
    *,
    require_explicit_resource: bool = False,
) -> bool:
    """Boolean form of :func:`require_scope`. Structurally invalid claims still
    raise :class:`WorkContextError` — "invalid" is never reported as ``False``."""
    try:
        require_scope(
            context,
            resource_kind,
            action,
            resource_id,
            require_explicit_resource=require_explicit_resource,
        )
    except WorkContextDenied:
        return False
    return True


# --------------------------------------------------------------------------- #
# Payload (de)serialization — one fixed snake_case JSON layout
# --------------------------------------------------------------------------- #

_STRING_FIELDS = (
    "typ",
    "algorithm",
    "key_id",
    "issuer",
    "audience",
    "nonce",
    "authorization_revision",
    "replay_policy",
    "tenant_id",
    "owner_principal_id",
    "task_id",
    "session_id",
)
_INT_FIELDS = ("not_before_unix", "issued_at_unix", "expires_at_unix")
_OPTIONAL_STRING_FIELDS = ("parent_session_id", "workspace_id", "project_id")
_LIST_FIELDS = ("authority_scopes", "actor_chain", "attribution_team_ids")
_KNOWN_FIELDS = frozenset(_STRING_FIELDS + _INT_FIELDS + _OPTIONAL_STRING_FIELDS + _LIST_FIELDS)


def _unmarshal(payload: bytes) -> WorkContext:
    """Strict decode, as Go's ``DisallowUnknownFields`` decoder: unknown keys,
    trailing data, wrong JSON types, and a non-uint64 ``authorization_revision``
    are all errors. JSON ``null`` reads as the field's zero value (Go's rule).

    Stricter than Go in one respect: keys are matched case-sensitively
    (``encoding/json`` would also accept ``"Issuer"``). No signer emits that.
    """
    try:
        text = payload.decode("utf-8")
        document = json.loads(text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise WorkContextError(f"decode payload: {exc}") from exc
    if not isinstance(document, dict):
        raise WorkContextError("decode payload: payload is not a JSON object")
    unknown = set(document) - _KNOWN_FIELDS
    if unknown:
        raise WorkContextError(f"decode payload: unknown field {min(unknown)!r}")

    strings = {name: _as_string(document, name) for name in _STRING_FIELDS}
    ints = {name: _as_int64(document, name) for name in _INT_FIELDS}
    optionals = {name: _as_optional_string(document, name) for name in _OPTIONAL_STRING_FIELDS}

    revision_text = strings.pop("authorization_revision")
    if not _UINT64_DECIMAL.fullmatch(revision_text) or int(revision_text) > _UINT64_MAX:
        raise WorkContextError("authorization_revision must be uint64 decimal")

    return WorkContext(
        **strings,
        **ints,
        **optionals,
        authorization_revision=int(revision_text),
        authority_scopes=_as_scopes(document, "authority_scopes"),
        actor_chain=_as_actors(document, "actor_chain"),
        attribution_team_ids=_as_string_list(document, "attribution_team_ids"),
    )


def _as_string(document: Mapping[str, Any], name: str) -> str:
    value = document.get(name)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise WorkContextError(f"decode payload: {name} must be a string")
    return value


def _as_optional_string(document: Mapping[str, Any], name: str) -> str | None:
    value = document.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkContextError(f"decode payload: {name} must be a string")
    return value


def _as_int64(document: Mapping[str, Any], name: str) -> int:
    value = document.get(name)
    if value is None:
        return 0
    # bool is an int subclass in Python; Go rejects JSON true/false for int64.
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkContextError(f"decode payload: {name} must be an integer")
    if value < _INT64_MIN or value > _INT64_MAX:
        raise WorkContextError(f"decode payload: {name} overflows int64")
    return value


def _as_list(document: Mapping[str, Any], name: str) -> list[Any]:
    value = document.get(name)
    if value is None:
        return []
    if not isinstance(value, list):
        raise WorkContextError(f"decode payload: {name} must be an array")
    return value


def _as_string_list(document: Mapping[str, Any], name: str) -> tuple[str, ...]:
    values = _as_list(document, name)
    out: list[str] = []
    for value in values:
        if value is None:
            out.append("")
        elif isinstance(value, str):
            out.append(value)
        else:
            raise WorkContextError(f"decode payload: {name} must contain strings")
    return tuple(out)


def _as_scopes(document: Mapping[str, Any], name: str) -> tuple[WorkScope, ...]:
    out: list[WorkScope] = []
    for index, entry in enumerate(_as_list(document, name)):
        if entry is None:
            entry = {}
        if not isinstance(entry, dict):
            raise WorkContextError(f"decode payload: {name}[{index}] must be an object")
        unknown = set(entry) - {"resource_kind", "actions", "resource_ids"}
        if unknown:
            raise WorkContextError(
                f"decode payload: unknown field {min(unknown)!r} in {name}[{index}]"
            )
        out.append(
            WorkScope(
                resource_kind=_as_string(entry, "resource_kind"),
                actions=_as_string_list(entry, "actions"),
                resource_ids=_as_string_list(entry, "resource_ids"),
            )
        )
    return tuple(out)


def _as_actors(document: Mapping[str, Any], name: str) -> tuple[WorkActor, ...]:
    out: list[WorkActor] = []
    for index, entry in enumerate(_as_list(document, name)):
        if entry is None:
            entry = {}
        if not isinstance(entry, dict):
            raise WorkContextError(f"decode payload: {name}[{index}] must be an object")
        unknown = set(entry) - {"principal_id", "principal_kind", "delegation_id", "granted_scopes"}
        if unknown:
            raise WorkContextError(
                f"decode payload: unknown field {min(unknown)!r} in {name}[{index}]"
            )
        out.append(
            WorkActor(
                principal_id=_as_string(entry, "principal_id"),
                principal_kind=_as_string(entry, "principal_kind"),
                delegation_id=_as_string(entry, "delegation_id"),
                granted_scopes=_as_scopes(entry, "granted_scopes"),
            )
        )
    return tuple(out)


def _scope_to_dict(scope: WorkScope) -> dict[str, Any]:
    return {
        "resource_kind": scope.resource_kind,
        "actions": list(scope.actions),
        "resource_ids": list(scope.resource_ids),
    }


# --------------------------------------------------------------------------- #
# Structural validation — sdk-go's validateWorkContext, same checks, same order
# --------------------------------------------------------------------------- #


def _validate(context: WorkContext) -> None:
    if not isinstance(context, WorkContext):
        raise WorkContextError("nil claims")
    if context.typ != WORK_CONTEXT_TYPE:
        raise WorkContextError(f"unsupported typ {context.typ!r}")
    if context.algorithm != WORK_CONTEXT_ALGORITHM:
        raise WorkContextError(f"unsupported algorithm {context.algorithm!r}")
    for name, value, limit in (
        ("key_id", context.key_id, _MAX_KIND_BYTES),
        ("issuer", context.issuer, _MAX_ID_BYTES),
        ("audience", context.audience, _MAX_ID_BYTES),
        ("nonce", context.nonce, _MAX_ID_BYTES),
        ("tenant_id", context.tenant_id, _MAX_ID_BYTES),
        ("owner_principal_id", context.owner_principal_id, _MAX_ID_BYTES),
        ("task_id", context.task_id, _MAX_ID_BYTES),
        ("session_id", context.session_id, _MAX_ID_BYTES),
    ):
        _validate_bounded(name, value, limit, required=True)
    for name, value in (
        ("parent_session_id", context.parent_session_id),
        ("workspace_id", context.workspace_id),
        ("project_id", context.project_id),
    ):
        _validate_bounded(name, value or "", _MAX_ID_BYTES, required=False)
    if context.parent_session_id is not None and context.parent_session_id == context.session_id:
        raise WorkContextError("parent session equals session")
    if context.replay_policy not in (REPLAY_IDEMPOTENT, REPLAY_SINGLE_USE):
        raise WorkContextError(f"unsupported replay policy {context.replay_policy!r}")
    if context.not_before_unix > context.expires_at_unix:
        raise WorkContextError("not-before is after expiry")
    if context.issued_at_unix > context.expires_at_unix:
        raise WorkContextError("issued-at is after expiry")
    ttl = context.expires_at_unix - context.issued_at_unix
    if ttl <= 0 or ttl > MAX_TTL_SECONDS:
        raise WorkContextError(f"lifetime must be positive and at most {MAX_TTL_SECONDS}s")
    if len(context.actor_chain) > MAX_ACTOR_DEPTH:
        raise WorkContextError(f"actor chain exceeds depth {MAX_ACTOR_DEPTH}")
    if len(context.attribution_team_ids) > _MAX_SCOPE_ENTRIES:
        raise WorkContextError("too many attribution teams")
    _validate_sorted_unique(
        "attribution_team_ids", context.attribution_team_ids, _MAX_ID_BYTES, required=True
    )
    _validate_scopes("authority_scopes", context.authority_scopes)
    previous = context.authority_scopes
    for index, actor in enumerate(context.actor_chain):
        if not isinstance(actor, WorkActor):
            raise WorkContextError(f"actor_chain[{index}] is nil")
        _validate_bounded("actor principal_id", actor.principal_id, _MAX_ID_BYTES, required=True)
        _validate_bounded(
            "actor principal_kind", actor.principal_kind, _MAX_KIND_BYTES, required=True
        )
        _validate_bounded("actor delegation_id", actor.delegation_id, _MAX_ID_BYTES, required=True)
        _validate_scopes(f"actor_chain[{index}].granted_scopes", actor.granted_scopes)
        if not _scopes_attenuate(previous, actor.granted_scopes):
            raise WorkContextError(f"actor_chain[{index}] widens authority")
        previous = actor.granted_scopes


def _validate_scopes(name: str, scopes: Sequence[WorkScope]) -> None:
    if len(scopes) > _MAX_SCOPES:
        raise WorkContextError(f"{name} exceeds {_MAX_SCOPES} scopes")
    previous_kind = ""
    for index, scope in enumerate(scopes):
        if not isinstance(scope, WorkScope):
            raise WorkContextError(f"{name}[{index}] is nil")
        _validate_bounded(
            f"{name} resource_kind", scope.resource_kind, _MAX_KIND_BYTES, required=True
        )
        if previous_kind >= scope.resource_kind:
            raise WorkContextError(f"{name} resource kinds must be sorted and unique")
        previous_kind = scope.resource_kind
        if len(scope.actions) == 0 or len(scope.actions) > _MAX_SCOPE_ENTRIES:
            raise WorkContextError(
                f"{name}[{index}] actions must contain 1..{_MAX_SCOPE_ENTRIES} entries"
            )
        _validate_sorted_unique(f"{name} actions", scope.actions, _MAX_KIND_BYTES, required=True)
        if len(scope.resource_ids) > _MAX_SCOPE_ENTRIES:
            raise WorkContextError(f"{name}[{index}] has too many resource IDs")
        _validate_sorted_unique(
            f"{name} resource_ids", scope.resource_ids, _MAX_ID_BYTES, required=True
        )


def _scopes_attenuate(parent: Sequence[WorkScope], child: Sequence[WorkScope]) -> bool:
    """A child hop may only narrow: same kinds, subset of actions, and an
    explicit parent ``resource_ids`` set can shrink to another non-empty
    subset but never widen back to the wildcard."""
    parent_by_kind = {scope.resource_kind: scope for scope in parent}
    for scope in child:
        ancestor = parent_by_kind.get(scope.resource_kind)
        if ancestor is None or not set(scope.actions) <= set(ancestor.actions):
            return False
        if ancestor.resource_ids and (
            not scope.resource_ids or not set(scope.resource_ids) <= set(ancestor.resource_ids)
        ):
            return False
    return True


def _validate_sorted_unique(
    name: str, values: Sequence[str], limit: int, *, required: bool
) -> None:
    previous = ""
    for index, value in enumerate(values):
        _validate_bounded(name, value, limit, required=required)
        if index > 0 and previous >= value:
            raise WorkContextError(f"{name} must be sorted and unique")
        previous = value


def _validate_bounded(name: str, value: str, limit: int, *, required: bool) -> None:
    if not isinstance(value, str):
        raise WorkContextError(f"{name} must be a string")
    if required and value.strip() == "":
        raise WorkContextError(f"{name} is required")
    if len(value.encode("utf-8")) > limit:
        raise WorkContextError(f"{name} exceeds {limit} bytes")
