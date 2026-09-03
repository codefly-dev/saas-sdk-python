"""Codefly Work Contexts — both halves of the ``x-codefly-work-context`` feature,
the Python twin of ``sdk-go``'s ``work_context.go``/``work_context_jwks.go``.

A Work Context is a header carrying a delegated authority capability. This module
covers the two sides a solution needs:

* **Mint side** — :func:`new` / :class:`Client` bind to a solution-runtime
  gateway and mint short-lived contexts at the accounts ``WorkContextService``
  (``start_task`` / ``exchange_audience`` / ``renew``); :func:`attach` stamps a
  minted token on outgoing calls. Only the *client* to the authority is here —
  the signer itself stays authority-side in ``sdk-go``.
* **Callee side** — :class:`Verifier` / :class:`JWKSVerifier` *verify* a
  presented context so a service can act on delegated authority.

The wire format is **not a JWT**: a token is ``base64url(payload).base64url(sig)``
where ``payload`` is a fixed snake_case JSON object, ``sig`` is a raw 64-byte
Ed25519 signature over the exact payload bytes, and ``key_id`` lives *inside* the
payload. Field order, uint64-as-decimal-string encoding, scope sorting, and
base64url are pinned byte-for-byte to ``sdk-go`` (see the wire golden in
``tests/fixtures``), so a token minted by any Codefly SDK verifies identically
here.

Two verifiers are provided:

* :class:`Verifier` — a fixed set of Ed25519 public keys, keyed by ``key_id``.
* :class:`JWKSVerifier` — rotation-aware discovery through a published JWKS
  endpoint, cached with a TTL and an unknown-key refresh, plus an explicit
  :meth:`JWKSVerifier.refresh` for fail-closed boot.

Trust is established in this order: two-segment shape, key lookup, Ed25519
signature, structural validation (including the proto's ``min_len`` constraints
and monotonic scope attenuation), time window, then the caller's expectations.
"""

from __future__ import annotations

import base64
import binascii
import json
import threading
import urllib.error
import urllib.request
from collections.abc import MutableMapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol, TypeVar
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from saas_sdk._gen import work_contexts_pb2 as pb

__all__ = [
    "WORK_CONTEXT_HEADER",
    "HEADER_NAME",
    "WORK_CONTEXT_TYPE",
    "WORK_CONTEXT_ALGORITHM",
    "REPLAY_IDEMPOTENT",
    "REPLAY_SINGLE_USE",
    "DEFAULT_TTL",
    "MAX_TTL",
    "WorkContextError",
    "WorkContextDenied",
    "WorkContextMintError",
    "WorkScope",
    "WorkActor",
    "WorkContext",
    "Expectations",
    "ScopeRequirement",
    "Verifier",
    "JWKSVerifier",
    "Client",
    "Gateway",
    "require_scope",
    "token_from_headers",
    "attach",
    "new",
    "pb",
]

WORK_CONTEXT_HEADER = "x-codefly-work-context"
# Mint-side alias for the same carrier, matching sdk-go's WorkContextHeaderName.
HEADER_NAME = WORK_CONTEXT_HEADER
WORK_CONTEXT_TYPE = "codefly.work-context/v1"
WORK_CONTEXT_ALGORITHM = "Ed25519"

REPLAY_IDEMPOTENT = "idempotent"
REPLAY_SINGLE_USE = "single-use"

# Issuance TTL bounds, matching sdk-go's WorkContextDefaultTTL / WorkContextMaxTTL.
DEFAULT_TTL = timedelta(minutes=5)
MAX_TTL = timedelta(minutes=15)

_MAX_TOKEN_BYTES = 32 * 1024
_MAX_ID_BYTES = 512
_MAX_KIND_BYTES = 128
_MAX_SCOPES = 64
_MAX_SCOPE_ENTRIES = 256
_MAX_ACTOR_DEPTH = 16
_ED25519_PUBLIC_KEY_SIZE = 32
_ED25519_SIGNATURE_SIZE = 64
_UINT64_MAX = (1 << 64) - 1

_MAX_TTL = timedelta(minutes=15)
_CLOCK_SKEW = timedelta(minutes=1)

_JWKS_DEFAULT_CACHE_TTL = timedelta(minutes=5)
_JWKS_MAX_CACHE_TTL = timedelta(hours=24)
_JWKS_DEFAULT_REQUEST_TIMEOUT = timedelta(seconds=2)
_JWKS_MAX_REQUEST_TIMEOUT = timedelta(seconds=30)
_JWKS_MAX_BYTES = 256 * 1024
_JWKS_MAX_KEYS = 64
# After a scheduled refresh fails, hold the failure for this long instead of
# re-fetching on the very next request. Without it, an expired cache plus a down
# JWKS endpoint turns *every* inbound verify into a fresh upstream fetch — each
# blocking under the lock for up to the request timeout — so a brief outage
# amplifies into a serialized request pile-up. Fail-closed is preserved: callers
# inside the window get the cached failure, never stale keys.
_JWKS_FAILED_REFRESH_BACKOFF = timedelta(seconds=5)

_NowFn = Callable[[], datetime]


class WorkContextError(Exception):
    """A Work Context is malformed, unverifiable, or fails a constraint. Raised
    for every failure that is not a scope denial; verification fails closed."""


class WorkContextDenied(WorkContextError):
    """A structurally valid, verified Work Context does not grant a required
    scope. Distinct from :class:`WorkContextError` so authorization misses can be
    told apart from invalid capabilities."""


@dataclass(frozen=True)
class WorkScope:
    resource_kind: str
    actions: tuple[str, ...]
    resource_ids: tuple[str, ...]


@dataclass(frozen=True)
class WorkActor:
    principal_id: str
    principal_kind: str
    delegation_id: str
    granted_scopes: tuple[WorkScope, ...]


@dataclass(frozen=True)
class WorkContext:
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
    parent_session_id: str | None
    authority_scopes: tuple[WorkScope, ...]
    actor_chain: tuple[WorkActor, ...]
    attribution_team_ids: tuple[str, ...]
    workspace_id: str | None
    project_id: str | None

    def effective_scopes(self) -> tuple[WorkScope, ...]:
        """The scopes that authorize the current hop: the final actor's granted
        scopes when a delegation chain is present, otherwise the owner's
        authority scopes."""
        if self.actor_chain:
            return self.actor_chain[-1].granted_scopes
        return self.authority_scopes


@dataclass(frozen=True)
class Expectations:
    """Values the callee requires the context to carry. An empty string (or
    ``None`` pointer field) means "do not constrain"; a set value must match
    exactly or verification fails."""

    issuer: str = ""
    audience: str = ""
    tenant_id: str = ""
    owner_principal_id: str = ""
    task_id: str = ""
    session_id: str = ""
    parent_session_id: str | None = None
    authorization_revision: int | None = None


@dataclass(frozen=True)
class ScopeRequirement:
    """One exact capability a verified context must grant. An empty
    ``resource_id`` asks whether the effective scope grants every resource of
    ``resource_kind``; it never ignores an explicit resource restriction unless
    ``require_explicit_resource`` is set to force an explicit-ID match."""

    resource_kind: str
    action: str
    resource_id: str = ""
    require_explicit_resource: bool = False


def token_from_headers(headers) -> str:
    """Extract the opaque Work Context token from a mapping of request headers.
    Does not verify it; pass the result to a verifier."""
    if headers is None:
        raise WorkContextError("missing HTTP headers")
    encoded = headers.get(WORK_CONTEXT_HEADER) or headers.get(WORK_CONTEXT_HEADER.title()) or ""
    return encoded


class Verifier:
    """Verifies signed Work Contexts against a fixed set of Ed25519 public keys.

    ``public_keys`` maps ``key_id`` to a raw 32-byte Ed25519 public key. ``now``
    supplies the current time (an aware UTC :class:`datetime`) for the time
    window and defaults to the system clock. ``clock_skew`` tolerates bounded
    clock drift and may not exceed one minute.
    """

    def __init__(
        self,
        public_keys: dict[str, bytes],
        *,
        now: _NowFn | None = None,
        clock_skew: timedelta = _CLOCK_SKEW,
    ) -> None:
        if not public_keys:
            raise WorkContextError("no public verification keys")
        keys: dict[str, Ed25519PublicKey] = {}
        for key_id, raw in public_keys.items():
            _validate_bounded("key_id", key_id, _MAX_KIND_BYTES, required=True)
            if len(raw) != _ED25519_PUBLIC_KEY_SIZE:
                raise WorkContextError(
                    f"public key {key_id!r} must be {_ED25519_PUBLIC_KEY_SIZE} bytes"
                )
            keys[key_id] = Ed25519PublicKey.from_public_bytes(bytes(raw))
        if clock_skew < timedelta(0) or clock_skew > _CLOCK_SKEW:
            raise WorkContextError(f"clock skew must be between zero and {_CLOCK_SKEW}")
        self._keys = keys
        self._now = now or _system_now
        self._clock_skew = clock_skew

    def verify(self, encoded: str, expected: Expectations = Expectations()) -> WorkContext:
        """Verify a presented token and return its claims, or raise
        :class:`WorkContextError`. The signature is checked over the exact
        payload bytes, so any tampering fails closed before claims are read."""
        payload, signature = _decode_token(encoded)
        key_id = _probe_key_id(payload)
        public_key = self._keys.get(key_id)
        if public_key is None:
            raise WorkContextError(f"unknown key id {key_id!r}")
        try:
            public_key.verify(signature, payload)
        except InvalidSignature:
            raise WorkContextError("signature verification failed") from None
        context = _unmarshal(payload)
        _validate_work_context(context)
        self._validate_time(context)
        _match_expectations(context, expected)
        return context

    def _validate_time(self, context: WorkContext) -> None:
        now = self._now().timestamp()
        skew = self._clock_skew.total_seconds()
        if now < context.not_before_unix - skew:
            raise WorkContextError("token is not active yet")
        if context.issued_at_unix > now + skew:
            raise WorkContextError("token was issued in the future")
        if now > context.expires_at_unix + skew:
            raise WorkContextError("token expired")


def require_scope(claims: WorkContext, requirement: ScopeRequirement) -> None:
    """Authorize ``requirement`` against a verified context's effective scope, or
    raise :class:`WorkContextDenied`. Claims are structurally revalidated first
    so a hand-constructed or mutated context cannot authorize by accident."""
    _validate_work_context(claims)
    _validate_bounded("required resource_kind", requirement.resource_kind, _MAX_KIND_BYTES, required=True)
    _validate_bounded("required action", requirement.action, _MAX_KIND_BYTES, required=True)
    _validate_bounded(
        "required resource_id",
        requirement.resource_id,
        _MAX_ID_BYTES,
        required=requirement.require_explicit_resource,
    )
    for scope in claims.effective_scopes():
        if scope.resource_kind != requirement.resource_kind or requirement.action not in scope.actions:
            continue
        if not scope.resource_ids and not requirement.require_explicit_resource:
            return
        if requirement.resource_id and requirement.resource_id in scope.resource_ids:
            return
    raise WorkContextDenied(
        f"scope denied: {requirement.resource_kind}:{requirement.action}:{requirement.resource_id}"
    )


class JWKSVerifier:
    """Rotation-aware Work Context verifier backed by a published JWKS endpoint.

    Public keys are fetched from ``url`` (an absolute HTTP(S) URL without
    credentials, query, or fragment, e.g. ``/v1/auth/.well-known/jwks.json``),
    cached for ``cache_ttl``, and re-fetched on expiry. A token whose ``key_id``
    is not cached forces exactly one refresh per cache generation, so rotation is
    picked up immediately while attacker-supplied key IDs cannot turn
    verification into an unbounded request loop. Only public keys are cached;
    no bearer token is ever stored.

    :meth:`refresh` fetches eagerly so a service can fail closed at boot rather
    than on its first request.
    """

    def __init__(
        self,
        url: str,
        *,
        cache_ttl: timedelta = _JWKS_DEFAULT_CACHE_TTL,
        request_timeout: timedelta = _JWKS_DEFAULT_REQUEST_TIMEOUT,
        now: _NowFn | None = None,
        clock_skew: timedelta = _CLOCK_SKEW,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        self._url = _validate_jwks_url(url)
        if cache_ttl < timedelta(seconds=1) or cache_ttl > _JWKS_MAX_CACHE_TTL:
            raise WorkContextError(f"JWKS cache TTL must be between 1s and {_JWKS_MAX_CACHE_TTL}")
        if request_timeout < timedelta(milliseconds=1) or request_timeout > _JWKS_MAX_REQUEST_TIMEOUT:
            raise WorkContextError(
                f"JWKS request timeout must be between 1ms and {_JWKS_MAX_REQUEST_TIMEOUT}"
            )
        # Validate the skew eagerly, like cache_ttl and request_timeout, rather
        # than letting the Verifier reject it only when the first fetch builds it
        # — a misconfiguration should surface at construction, not on first
        # request.
        if clock_skew < timedelta(0) or clock_skew > _CLOCK_SKEW:
            raise WorkContextError(f"clock skew must be between zero and {_CLOCK_SKEW}")
        self._cache_ttl = cache_ttl
        self._request_timeout = request_timeout.total_seconds()
        self._now = now or _system_now
        self._clock_skew = clock_skew
        # A no-redirect opener: the JWKS URL is trusted; a redirect to another
        # host is a downgrade, not a legitimate rotation signal.
        self._opener = opener or urllib.request.build_opener(_NoRedirect())
        self._lock = threading.Lock()
        self._verifier: Verifier | None = None
        self._key_ids: frozenset[str] = frozenset()
        self._expires_at = 0.0
        self._generation = 0
        self._unknown_refresh_generation = 0
        # Negative cache for a failed scheduled refresh: fail closed from the
        # cached error until this moment rather than re-hitting the endpoint.
        self._retry_after = 0.0
        self._last_error: WorkContextError | None = None

    def refresh(self) -> None:
        """Fetch the JWKS now, replacing the cache. Call at startup to fail
        closed if key discovery is unavailable."""
        with self._lock:
            self._refresh_locked()
            self._unknown_refresh_generation = 0

    def verify(self, encoded: str, expected: Expectations = Expectations()) -> WorkContext:
        """Verify a presented token against the cached JWKS, refreshing once for
        an unknown key id before failing closed."""
        key_id = _probe_key_id(_decode_token(encoded)[0])
        verifier, key_ids, generation = self._current()
        if key_id in key_ids:
            return verifier.verify(encoded, expected)
        verifier, _, _ = self._refresh_unknown(generation)
        return verifier.verify(encoded, expected)

    def _current(self) -> tuple[Verifier, frozenset[str], int]:
        with self._lock:
            now = self._now().timestamp()
            if self._verifier is not None and now < self._expires_at:
                return self._verifier, self._key_ids, self._generation
            if now < self._retry_after:
                # A recent scheduled refresh failed; fail closed with the cached
                # error instead of hitting the endpoint again on every request.
                raise self._last_error  # set together with _retry_after
            verifier, key_ids, generation = self._refresh_locked()
            # A fresh TTL window may spend one unknown-key refresh on rotation.
            self._unknown_refresh_generation = 0
            return verifier, key_ids, generation

    def _refresh_unknown(self, observed_generation: int) -> tuple[Verifier, frozenset[str], int]:
        with self._lock:
            if self._verifier is not None and self._generation != observed_generation:
                return self._verifier, self._key_ids, self._generation
            if self._verifier is not None and self._unknown_refresh_generation == self._generation:
                return self._verifier, self._key_ids, self._generation
            # Reserve this generation before network I/O so a failed rotation
            # refresh cannot let attacker-controlled key ids loop the endpoint.
            self._unknown_refresh_generation = self._generation
            verifier, key_ids, generation = self._refresh_locked()
            self._unknown_refresh_generation = generation
            return verifier, key_ids, generation

    def _refresh_locked(self) -> tuple[Verifier, frozenset[str], int]:
        try:
            keys = self._fetch()
            verifier = Verifier(keys, now=self._now, clock_skew=self._clock_skew)
        except WorkContextError as error:
            # Open a short backoff window so a failed refresh does not re-hit the
            # endpoint on the next request (avoids an outage-driven fetch storm).
            self._retry_after = self._now().timestamp() + _JWKS_FAILED_REFRESH_BACKOFF.total_seconds()
            self._last_error = error
            raise
        self._verifier = verifier
        self._key_ids = frozenset(keys)
        self._expires_at = self._now().timestamp() + self._cache_ttl.total_seconds()
        self._retry_after = 0.0
        self._last_error = None
        self._generation += 1
        return verifier, self._key_ids, self._generation

    def _fetch(self) -> dict[str, bytes]:
        request = urllib.request.Request(
            self._url, headers={"Accept": "application/json"}, method="GET"
        )
        try:
            response = self._opener.open(request, timeout=self._request_timeout)
        except urllib.error.HTTPError as error:
            raise WorkContextError(f"Work Context JWKS returned HTTP {error.code}") from None
        except (urllib.error.URLError, OSError) as error:
            raise WorkContextError(f"fetch Work Context JWKS: {error}") from None
        with response:
            content_type = response.headers.get("Content-Type")
            if content_type and content_type.split(";", 1)[0].strip().lower() != "application/json":
                raise WorkContextError("Work Context JWKS is not application/json")
            payload = response.read(_JWKS_MAX_BYTES + 1)
        if len(payload) > _JWKS_MAX_BYTES:
            raise WorkContextError(f"Work Context JWKS exceeds {_JWKS_MAX_BYTES} bytes")
        return _parse_jwks(payload)


def _parse_jwks(payload: bytes) -> dict[str, bytes]:
    try:
        document = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as error:
        raise WorkContextError(f"decode Work Context JWKS: {error}") from None
    keys = document.get("keys") if isinstance(document, dict) else None
    if not isinstance(keys, list) or not 1 <= len(keys) <= _JWKS_MAX_KEYS:
        raise WorkContextError(
            f"Work Context JWKS must contain between 1 and {_JWKS_MAX_KEYS} keys"
        )
    result: dict[str, bytes] = {}
    for key in keys:
        if not isinstance(key, dict):
            raise WorkContextError("JWKS contains a non-object key")
        if (
            key.get("kty") != "OKP"
            or key.get("crv") != "Ed25519"
            or key.get("alg", "") not in ("", "EdDSA")
            or key.get("use", "") not in ("", "sig")
        ):
            raise WorkContextError("JWKS contains a non-Ed25519 signing key")
        key_id = key.get("kid", "")
        if not isinstance(key_id, str):
            raise WorkContextError("JWKS key id must be a string")
        _validate_bounded("key_id", key_id, _MAX_KIND_BYTES, required=True)
        x = key.get("x", "")
        try:
            decoded = _b64url_decode(x) if isinstance(x, str) else b""
        except WorkContextError:
            decoded = b""
        if len(decoded) != _ED25519_PUBLIC_KEY_SIZE:
            raise WorkContextError(f"JWKS key {key_id!r} has an invalid Ed25519 public key")
        if key_id in result:
            raise WorkContextError(f"JWKS has duplicate key id {key_id!r}")
        result[key_id] = decoded
    return result


def _validate_jwks_url(raw: str) -> str:
    parts = urlsplit(raw.strip())
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        raise WorkContextError(
            "Work Context JWKS URL must be an absolute HTTP(S) URL without "
            "credentials, query, or fragment"
        )
    return parts.geturl()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


# --- wire decoding & structural validation -------------------------------------


def _decode_token(encoded: str) -> tuple[bytes, bytes]:
    _validate_token_shape(encoded)
    payload_segment, signature_segment = encoded.split(".", 1)
    payload = _decode_canonical(payload_segment, "payload")
    signature = _decode_canonical(signature_segment, "signature")
    if len(signature) != _ED25519_SIGNATURE_SIZE:
        raise WorkContextError(f"signature must be {_ED25519_SIGNATURE_SIZE} bytes")
    return payload, signature


def _validate_token_shape(encoded: str) -> None:
    if not encoded:
        raise WorkContextError("empty token")
    if len(encoded.encode("utf-8")) > _MAX_TOKEN_BYTES:
        raise WorkContextError(f"token exceeds {_MAX_TOKEN_BYTES} bytes")
    if encoded.count(".") != 1:
        raise WorkContextError("token must have exactly two segments")


def _decode_canonical(segment: str, name: str) -> bytes:
    try:
        decoded = _b64url_decode(segment)
    except WorkContextError:
        raise WorkContextError(f"{name} base64 is invalid") from None
    if _b64url_encode(decoded) != segment:
        raise WorkContextError(f"{name} is not canonical base64url")
    return decoded


def _probe_key_id(payload: bytes) -> str:
    try:
        document = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as error:
        raise WorkContextError(f"decode key id: {error}") from None
    key_id = document.get("key_id", "") if isinstance(document, dict) else ""
    if not isinstance(key_id, str):
        raise WorkContextError("key id must be a string")
    _validate_bounded("key_id", key_id, _MAX_KIND_BYTES, required=True)
    return key_id


_CONTEXT_KEYS = frozenset(
    {
        "typ",
        "algorithm",
        "key_id",
        "issuer",
        "audience",
        "not_before_unix",
        "issued_at_unix",
        "expires_at_unix",
        "nonce",
        "authorization_revision",
        "replay_policy",
        "tenant_id",
        "owner_principal_id",
        "task_id",
        "session_id",
        "parent_session_id",
        "authority_scopes",
        "actor_chain",
        "attribution_team_ids",
        "workspace_id",
        "project_id",
    }
)
_SCOPE_KEYS = frozenset({"resource_kind", "actions", "resource_ids"})
_ACTOR_KEYS = frozenset({"principal_id", "principal_kind", "delegation_id", "granted_scopes"})


def _unmarshal(payload: bytes) -> WorkContext:
    try:
        document = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as error:
        raise WorkContextError(f"decode payload: {error}") from None
    if not isinstance(document, dict):
        raise WorkContextError("payload must be a JSON object")
    _reject_unknown(document, _CONTEXT_KEYS, "payload")
    revision = _parse_uint64(_require_str(document, "authorization_revision"))
    return WorkContext(
        typ=_require_str(document, "typ"),
        algorithm=_require_str(document, "algorithm"),
        key_id=_require_str(document, "key_id"),
        issuer=_require_str(document, "issuer"),
        audience=_require_str(document, "audience"),
        not_before_unix=_require_int(document, "not_before_unix"),
        issued_at_unix=_require_int(document, "issued_at_unix"),
        expires_at_unix=_require_int(document, "expires_at_unix"),
        nonce=_require_str(document, "nonce"),
        authorization_revision=revision,
        replay_policy=_require_str(document, "replay_policy"),
        tenant_id=_require_str(document, "tenant_id"),
        owner_principal_id=_require_str(document, "owner_principal_id"),
        task_id=_require_str(document, "task_id"),
        session_id=_require_str(document, "session_id"),
        parent_session_id=_optional_str(document, "parent_session_id"),
        authority_scopes=_parse_scopes(document.get("authority_scopes")),
        actor_chain=_parse_actors(document.get("actor_chain")),
        attribution_team_ids=_require_str_list(document, "attribution_team_ids"),
        workspace_id=_optional_str(document, "workspace_id"),
        project_id=_optional_str(document, "project_id"),
    )


def _parse_scopes(raw) -> tuple[WorkScope, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise WorkContextError("scopes must be a JSON array")
    scopes = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise WorkContextError("scope must be a JSON object")
        _reject_unknown(entry, _SCOPE_KEYS, "scope")
        scopes.append(
            WorkScope(
                resource_kind=_require_str(entry, "resource_kind"),
                actions=_require_str_list(entry, "actions"),
                resource_ids=_require_str_list(entry, "resource_ids"),
            )
        )
    return tuple(scopes)


def _parse_actors(raw) -> tuple[WorkActor, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise WorkContextError("actor_chain must be a JSON array")
    actors = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise WorkContextError("actor must be a JSON object")
        _reject_unknown(entry, _ACTOR_KEYS, "actor")
        actors.append(
            WorkActor(
                principal_id=_require_str(entry, "principal_id"),
                principal_kind=_require_str(entry, "principal_kind"),
                delegation_id=_require_str(entry, "delegation_id"),
                granted_scopes=_parse_scopes(entry.get("granted_scopes")),
            )
        )
    return tuple(actors)


def _validate_work_context(context: WorkContext) -> None:
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
    # The proto declares min_len=1 on these optional fields, so a present value
    # must be non-empty even though the field itself may be absent. Independent
    # verifiers that skip this diverge on a security boundary (codefly-dev/sdk-go#7).
    for name, value in (
        ("parent_session_id", context.parent_session_id),
        ("workspace_id", context.workspace_id),
        ("project_id", context.project_id),
    ):
        if value is not None:
            _validate_bounded(name, value, _MAX_ID_BYTES, required=True)
    if context.parent_session_id is not None and context.parent_session_id == context.session_id:
        raise WorkContextError("parent session equals session")
    if context.replay_policy not in (REPLAY_IDEMPOTENT, REPLAY_SINGLE_USE):
        raise WorkContextError(f"unsupported replay policy {context.replay_policy!r}")
    if context.not_before_unix > context.expires_at_unix:
        raise WorkContextError("not-before is after expiry")
    if context.issued_at_unix > context.expires_at_unix:
        raise WorkContextError("issued-at is after expiry")
    ttl = context.expires_at_unix - context.issued_at_unix
    if ttl <= 0 or ttl > _MAX_TTL.total_seconds():
        raise WorkContextError(f"lifetime must be positive and at most {_MAX_TTL}")
    if len(context.actor_chain) > _MAX_ACTOR_DEPTH:
        raise WorkContextError(f"actor chain exceeds depth {_MAX_ACTOR_DEPTH}")
    if len(context.attribution_team_ids) > _MAX_SCOPE_ENTRIES:
        raise WorkContextError("too many attribution teams")
    _validate_sorted_unique("attribution_team_ids", context.attribution_team_ids, _MAX_ID_BYTES)
    _validate_scopes("authority_scopes", context.authority_scopes)
    previous = context.authority_scopes
    for index, actor in enumerate(context.actor_chain):
        _validate_bounded("actor principal_id", actor.principal_id, _MAX_ID_BYTES, required=True)
        _validate_bounded("actor principal_kind", actor.principal_kind, _MAX_KIND_BYTES, required=True)
        _validate_bounded("actor delegation_id", actor.delegation_id, _MAX_ID_BYTES, required=True)
        _validate_scopes(f"actor_chain[{index}].granted_scopes", actor.granted_scopes)
        if not _scopes_attenuate(previous, actor.granted_scopes):
            raise WorkContextError(f"actor_chain[{index}] widens authority")
        previous = actor.granted_scopes


def _validate_scopes(name: str, scopes: tuple[WorkScope, ...]) -> None:
    if len(scopes) > _MAX_SCOPES:
        raise WorkContextError(f"{name} exceeds {_MAX_SCOPES} scopes")
    previous_kind = ""
    for index, scope in enumerate(scopes):
        _validate_bounded(f"{name} resource_kind", scope.resource_kind, _MAX_KIND_BYTES, required=True)
        if previous_kind >= scope.resource_kind:
            raise WorkContextError(f"{name} resource kinds must be sorted and unique")
        previous_kind = scope.resource_kind
        if not 1 <= len(scope.actions) <= _MAX_SCOPE_ENTRIES:
            raise WorkContextError(
                f"{name}[{index}] actions must contain 1..{_MAX_SCOPE_ENTRIES} entries"
            )
        _validate_sorted_unique(f"{name} actions", scope.actions, _MAX_KIND_BYTES)
        if len(scope.resource_ids) > _MAX_SCOPE_ENTRIES:
            raise WorkContextError(f"{name}[{index}] has too many resource IDs")
        _validate_sorted_unique(f"{name} resource_ids", scope.resource_ids, _MAX_ID_BYTES)


def _scopes_attenuate(parent: tuple[WorkScope, ...], child: tuple[WorkScope, ...]) -> bool:
    parent_by_kind = {scope.resource_kind: scope for scope in parent}
    for scope in child:
        ancestor = parent_by_kind.get(scope.resource_kind)
        if ancestor is None or not _subset(scope.actions, ancestor.actions):
            return False
        # Empty parent resource_ids is a wildcard; an explicit parent set may
        # only be narrowed to another non-empty subset, never re-widened.
        if ancestor.resource_ids:
            if not scope.resource_ids or not _subset(scope.resource_ids, ancestor.resource_ids):
                return False
    return True


def _subset(child, parent) -> bool:
    parent_set = set(parent)
    return all(value in parent_set for value in child)


def _match_expectations(context: WorkContext, expected: Expectations) -> None:
    for name, got, want in (
        ("issuer", context.issuer, expected.issuer),
        ("audience", context.audience, expected.audience),
        ("tenant", context.tenant_id, expected.tenant_id),
        ("owner", context.owner_principal_id, expected.owner_principal_id),
        ("task", context.task_id, expected.task_id),
        ("session", context.session_id, expected.session_id),
    ):
        if want and got != want:
            raise WorkContextError(f"{name} mismatch")
    if expected.parent_session_id is not None and (context.parent_session_id or "") != expected.parent_session_id:
        raise WorkContextError("parent session mismatch")
    if (
        expected.authorization_revision is not None
        and context.authorization_revision != expected.authorization_revision
    ):
        raise WorkContextError("authorization revision mismatch")


def _validate_sorted_unique(name: str, values: tuple[str, ...], limit: int) -> None:
    previous = ""
    for index, value in enumerate(values):
        _validate_bounded(name, value, limit, required=True)
        if index > 0 and previous >= value:
            raise WorkContextError(f"{name} must be sorted and unique")
        previous = value


def _validate_bounded(name: str, value: str, limit: int, *, required: bool) -> None:
    # "Required" is the proto's min_len=1: a byte-length floor, not a trim. A
    # non-empty-but-whitespace id (e.g. " ") clears min_len and must be accepted
    # to keep bidirectional parity with sdk-go — an over-eager strip() would let
    # Python reject a token Go accepts.
    if required and value == "":
        raise WorkContextError(f"{name} is required")
    if len(value.encode("utf-8")) > limit:
        raise WorkContextError(f"{name} exceeds {limit} bytes")


# --- JSON field helpers --------------------------------------------------------


def _reject_unknown(document: dict, allowed: frozenset[str], where: str) -> None:
    unknown = document.keys() - allowed
    if unknown:
        raise WorkContextError(f"unknown {where} field {next(iter(sorted(unknown)))!r}")


def _require_str(document: dict, key: str) -> str:
    if key not in document:
        return ""
    value = document[key]
    if not isinstance(value, str):
        raise WorkContextError(f"{key} must be a string")
    return value


def _optional_str(document: dict, key: str) -> str | None:
    if key not in document:
        return None
    value = document[key]
    if not isinstance(value, str):
        raise WorkContextError(f"{key} must be a string")
    return value


def _require_int(document: dict, key: str) -> int:
    if key not in document:
        return 0
    value = document[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise WorkContextError(f"{key} must be an integer")
    return value


def _require_str_list(document: dict, key: str) -> tuple[str, ...]:
    if key not in document:
        return ()
    value = document[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkContextError(f"{key} must be an array of strings")
    return tuple(value)


def _parse_uint64(value: str) -> int:
    if not value or not value.isascii() or not value.isdigit():
        raise WorkContextError("authorization_revision must be a uint64 decimal")
    # Match Go's ParseUint (leading zeros allowed, "000…0" -> 0). Normalizing the
    # zeros away *before* int() also stops a pathological all-digit string past
    # CPython's 4300-digit conversion limit from escaping as a raw ValueError
    # instead of a WorkContextError. 2**64-1 is 20 digits, so anything longer
    # overflows and never reaches int().
    normalized = value.lstrip("0") or "0"
    if len(normalized) > 20 or int(normalized) > _UINT64_MAX:
        raise WorkContextError("authorization_revision must be a uint64 decimal")
    return int(normalized)


# --- base64url (raw, unpadded) -------------------------------------------------


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError) as error:
        raise WorkContextError(f"base64: {error}") from None


def _system_now() -> datetime:
    return datetime.now(timezone.utc)


# --- mint side: WorkContextService client --------------------------------------
#
# The callee half above verifies a presented context; the half below is the
# delegated caller that mints one at the accounts authority and stamps it on
# outgoing calls. Only the client to the authority lives here — the signer stays
# authority-side in sdk-go.

_M = TypeVar("_M")

_SERVICE = "/saas.accounts.v1.WorkContextService/"

_Headers = MutableMapping[str, str]


class WorkContextMintError(Exception):
    """A mint RPC (``StartTask`` / ``ExchangeAudience`` / ``RenewWorkContext``)
    was rejected or failed at the accounts service.

    Distinct from a verification failure so a delegated caller that both mints
    and verifies can tell a minting problem (this side) from a bad presented
    capability (the verify side).
    """

    def __init__(self, procedure: str, cause: object) -> None:
        self.procedure = procedure
        super().__init__(f"{procedure}: {cause}")


class Gateway(Protocol):
    """Transport seam the mint client needs from the solution runtime.

    Unlike the ambient-auth datasource gateway, ``unary`` takes the ``bearer``
    to present as the call's authorization, so the mint client can bind each
    owner-bound RPC to the user's token rather than the solution's own identity.
    """

    def unary(self, procedure: str, request, response_type: type[_M], *, bearer: str) -> _M: ...


class Client:
    """Entry point: ``new(gateway).start_task(...)``."""

    def __init__(self, gateway: Gateway) -> None:
        self._gateway = gateway

    def start_task(
        self,
        *,
        bearer: str,
        org_id: str,
        task_id: str,
        session_id: str,
        audience: str,
        scopes: Sequence[pb.WorkContextScope],
        actor_principal_id: str = "",
        ttl: timedelta | None = None,
        replay_policy: pb.WorkContextReplayPolicy = pb.WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED,
        workspace_id: str = "",
        project_id: str = "",
    ) -> pb.IssuedWorkContext:
        """Mint the root capability for a task and return the issued context.

        ``actor_principal_id`` empty means a direct human-owned task; otherwise
        it names the agent principal acting under the user's authority.
        """
        request = pb.StartTaskWorkContextRequest(
            org_id=org_id,
            task_id=task_id,
            session_id=session_id,
            audience=audience,
            authority_scopes=list(scopes),
            replay_policy=replay_policy,
            ttl_seconds=_ttl_seconds(ttl),
        )
        if actor_principal_id:
            request.actor_principal_id = actor_principal_id
        if workspace_id:
            request.workspace_id = workspace_id
        if project_id:
            request.project_id = project_id
        return self._mint("StartTask", request, bearer)

    def exchange_audience(
        self,
        *,
        bearer: str,
        parent: pb.IssuedWorkContext,
        audience: str,
        scopes: Sequence[pb.WorkContextScope],
        ttl: timedelta | None = None,
        replay_policy: pb.WorkContextReplayPolicy = pb.WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED,
    ) -> pb.IssuedWorkContext:
        """Reissue ``parent`` for one callee ``audience``, attenuating authority
        to ``scopes`` — the same task, session, and owner, never widened. Call
        once per distinct callee audience at turn start.
        """
        request = pb.ExchangeWorkContextAudienceRequest(
            org_id=parent.org_id,
            parent_work_context_token=parent.token,
            audience=audience,
            attenuated_scopes=list(scopes),
            replay_policy=replay_policy,
            ttl_seconds=_ttl_seconds(ttl),
        )
        return self._mint("ExchangeAudience", request, bearer)

    def renew(
        self,
        *,
        bearer: str,
        ctx: pb.IssuedWorkContext,
        audience: str | None = None,
        scopes: Sequence[pb.WorkContextScope] = (),
        ttl: timedelta | None = None,
        replay_policy: pb.WorkContextReplayPolicy = pb.WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED,
    ) -> pb.IssuedWorkContext:
        """Extend ``ctx`` with a fresh TTL for work running past the cap, using
        the current actor's ``bearer`` rather than the owner's.

        Empty or ``None`` ``audience`` keeps the parent's audience (the common
        TTL-only refresh); empty ``scopes`` keeps the actor's authority
        unchanged. Neither can widen the current actor's authority.
        """
        request = pb.RenewWorkContextRequest(
            org_id=ctx.org_id,
            parent_work_context_token=ctx.token,
            replay_policy=replay_policy,
            ttl_seconds=_ttl_seconds(ttl),
        )
        # Only stamp a non-empty audience: the field is an ``optional string``
        # with a server-side min_len=1, so an empty value present on the wire is
        # rejected rather than read as "keep the parent's".
        if audience:
            request.audience = audience
        if scopes:
            request.attenuated_scopes.extend(scopes)
        return self._mint("RenewWorkContext", request, bearer)

    def _mint(self, method: str, request, bearer: str) -> pb.IssuedWorkContext:
        try:
            return self._gateway.unary(
                _SERVICE + method, request, pb.IssuedWorkContext, bearer=bearer
            )
        except (WorkContextMintError, TypeError):
            # WorkContextMintError: a gateway that already speaks this error must
            # not be double-wrapped. TypeError: a gateway whose unary() lacks the
            # bearer keyword is a call-contract bug, not a mint failure — surface
            # it unmasked instead of hiding it as "the RPC failed".
            raise
        except Exception as err:  # transport / RPC failure — surface it as a mint error
            raise WorkContextMintError(method, err) from err


def _ttl_seconds(ttl: timedelta | None) -> int:
    # A zero duration means "use the default", matching sdk-go's signer (ttl==0
    # -> WorkContextDefaultTTL); it is never sent as 0 on the wire. Negative and
    # over-cap durations stay hard errors.
    resolved = DEFAULT_TTL if ttl is None or ttl == timedelta(0) else ttl
    seconds = round(resolved.total_seconds())
    if not 0 < seconds <= round(MAX_TTL.total_seconds()):
        raise ValueError(f"ttl must be positive and at most {MAX_TTL}; got {resolved}")
    return seconds


def _validated_token(token: str) -> str:
    if not token:
        raise ValueError("work context token is empty")
    if len(token.encode()) > _MAX_TOKEN_BYTES:
        raise ValueError("work context token exceeds 32 KiB")
    if token.count(".") != 1:
        raise ValueError("work context token must have exactly two segments")
    return token


def attach(request_or_headers: _Headers, ctx: pb.IssuedWorkContext) -> _Headers:
    """Stamp ``ctx``'s token on an outgoing call and return the target.

    ``request_or_headers`` is either a mutable header mapping or a request object
    exposing one as ``.headers``. This is a plain function (like sdk-go's
    ``AttachWorkContext``) — attaching needs no gateway or client state.
    """
    headers = getattr(request_or_headers, "headers", request_or_headers)
    headers[HEADER_NAME] = _validated_token(ctx.token)
    return request_or_headers


def new(gateway: Gateway) -> Client:
    """Bind the mint-side Work Context client to a solution runtime gateway."""
    return Client(gateway)
