"""Rotation-aware Work Context key discovery from the accounts JWKS — the twin
of ``sdk-go``'s ``work_context_jwks.go``.

accounts publishes its Ed25519 public key(s) at
``GET /v1/auth/.well-known/jwks.json`` as JWKs (``kty=OKP``, ``crv=Ed25519``,
``x`` = base64url of the 32 raw bytes, ``kid``). The Work Context signing key is
the same key as the access-token key, same ``kid``, so a callee that already
holds that JWKS for user tokens needs nothing more.

Transport is injected — pass any zero-argument callable returning the JWKS as
parsed JSON, a JSON string, or raw bytes — so this module takes no dependency on
an HTTP client. :func:`http_fetcher` is a stdlib default with sdk-go's hardening
(absolute http(s) URL, no redirects, ``application/json``, 256 KiB cap)::

    from saas_sdk import jwks, work_context as wc

    source = jwks.JWKSKeySource(jwks.http_fetcher("http://accounts:8080/v1/auth/.well-known/jwks.json"))
    ctx = source.verify(token, wc.WorkContextExpectations(issuer="saas-starter", audience="me"))

Caching mirrors Go: keys are held for ``cache_ttl``; an unknown ``kid`` forces
**one** early refresh per cache generation (rotation is picked up at once, but
attacker-chosen kids cannot turn verification into a request loop); a known
``kid`` with a bad signature never triggers I/O. It never fails open: no keys,
or a refresh that fails, is a :class:`~saas_sdk.work_context.WorkContextError`.
"""

from __future__ import annotations

import base64
import binascii
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime
from typing import Any

from saas_sdk.work_context import (
    WorkContext,
    WorkContextError,
    WorkContextExpectations,
    WorkContextVerifier,
    validate_token_shape,
)

__all__ = ["JWKSKeySource", "http_fetcher", "parse_jwks"]

DEFAULT_CACHE_TTL_SECONDS = 5 * 60
MAX_CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_REQUEST_TIMEOUT_SECONDS = 2.0
MAX_REQUEST_TIMEOUT_SECONDS = 30.0
MAX_JWKS_BYTES = 256 * 1024
MAX_JWKS_KEYS = 64

_MAX_KID_BYTES = 128
_PUBLIC_KEY_SIZE = 32

Fetcher = Callable[[], Any]


def parse_jwks(document: Any) -> dict[str, bytes]:
    """Load a JWKS (parsed JSON, JSON text, or bytes) into ``{kid: 32-byte
    Ed25519 public key}``. Every key must be an Ed25519 signing key; ``alg``
    and ``use``, when present, must be ``EdDSA`` / ``sig``. 1..64 keys, no
    duplicate ``kid``."""
    if isinstance(document, (bytes, bytearray)):
        if len(document) > MAX_JWKS_BYTES:
            raise WorkContextError(f"Work Context JWKS exceeds {MAX_JWKS_BYTES} bytes")
        document = bytes(document).decode("utf-8", errors="strict") if document else ""
    if isinstance(document, str):
        try:
            document = json.loads(document)
        except ValueError as exc:
            raise WorkContextError(f"decode Work Context JWKS: {exc}") from exc
    if not isinstance(document, dict):
        raise WorkContextError("decode Work Context JWKS: not a JSON object")
    entries = document.get("keys")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise WorkContextError("decode Work Context JWKS: keys must be an array")
    if not 1 <= len(entries) <= MAX_JWKS_KEYS:
        raise WorkContextError(f"Work Context JWKS must contain between 1 and {MAX_JWKS_KEYS} keys")
    keys: dict[str, bytes] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise WorkContextError("decode Work Context JWKS: key is not an object")
        if (
            entry.get("kty") != "OKP"
            or entry.get("crv") != "Ed25519"
            or entry.get("alg", "") not in ("", "EdDSA")
            or entry.get("use", "") not in ("", "sig")
        ):
            raise WorkContextError("JWKS contains a non-Ed25519 signing key")
        key_id = entry.get("kid", "")
        if not isinstance(key_id, str) or key_id.strip() == "":
            raise WorkContextError("key_id is required")
        if len(key_id.encode("utf-8")) > _MAX_KID_BYTES:
            raise WorkContextError(f"key_id exceeds {_MAX_KID_BYTES} bytes")
        x = entry.get("x", "")
        try:
            raw = x.encode("ascii")
            decoded = base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)
        except (AttributeError, UnicodeEncodeError, binascii.Error, ValueError):
            decoded = b""
        if len(decoded) != _PUBLIC_KEY_SIZE:
            raise WorkContextError(f"JWKS key {key_id!r} has an invalid Ed25519 public key")
        if key_id in keys:
            raise WorkContextError(f"JWKS has duplicate key ID {key_id!r}")
        keys[key_id] = decoded
    return keys


class JWKSKeySource:
    """A cached, rotation-aware key source over an injected JWKS fetcher.

    ``fetch`` is called with no arguments and returns the JWKS document (a
    dict, JSON text, or bytes); raise anything to signal failure. ``cache_ttl``
    is in seconds (1s..24h). ``now`` is injectable for tests and must agree
    with the verifier's clock, which it also drives.
    """

    def __init__(
        self,
        fetch: Fetcher,
        *,
        cache_ttl: float = DEFAULT_CACHE_TTL_SECONDS,
        clock_skew: float | None = None,
        now: Callable[[], float | datetime] = time.time,
    ) -> None:
        if not callable(fetch):
            raise WorkContextError("JWKS fetcher must be callable")
        if cache_ttl < 1 or cache_ttl > MAX_CACHE_TTL_SECONDS:
            raise WorkContextError(
                f"JWKS cache TTL must be between 1s and {MAX_CACHE_TTL_SECONDS}s"
            )
        self._fetch = fetch
        self._cache_ttl = float(cache_ttl)
        self._clock_skew = clock_skew
        self._now = now
        self._lock = threading.Lock()
        self._verifier: WorkContextVerifier | None = None
        self._keys: dict[str, bytes] = {}
        self._key_ids: frozenset[str] = frozenset()
        self._expires_at = 0.0
        self._generation = 0
        self._unknown_refresh_generation = -1

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        cache_ttl: float = DEFAULT_CACHE_TTL_SECONDS,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        clock_skew: float | None = None,
        now: Callable[[], float | datetime] = time.time,
    ) -> JWKSKeySource:
        """sdk-go's ``NewWorkContextJWKSVerifier`` shape: the JWKS URL and its
        bounds are validated now, without I/O; the first ``verify`` fetches.
        Uses :func:`http_fetcher`, so the transport guards are the Go ones."""
        return cls(
            http_fetcher(url, timeout=request_timeout),
            cache_ttl=cache_ttl,
            clock_skew=clock_skew,
            now=now,
        )

    # -- public -------------------------------------------------------------

    def keys(self) -> dict[str, bytes]:
        """The current key map (refreshing first if the cache expired)."""
        self._current()
        with self._lock:
            return dict(self._keys)

    def verifier(self) -> WorkContextVerifier:
        """A verifier over the current cached key set."""
        verifier, _, _ = self._current()
        return verifier

    def verify(
        self, encoded: str, expectations: WorkContextExpectations | None = None
    ) -> WorkContext:
        """Verify with the cached keys; on an unknown ``kid`` refresh once for
        this generation and retry."""
        key_id = _token_key_id(encoded)
        verifier, key_ids, generation = self._current()
        if key_id in key_ids:
            return verifier.verify(encoded, expectations)
        verifier = self._refresh_unknown(generation)
        return verifier.verify(encoded, expectations)

    # -- cache machinery (mirrors sdk-go) -------------------------------------

    def _now_unix(self) -> float:
        value = self._now()
        return value.timestamp() if isinstance(value, datetime) else float(value)

    def _current(self) -> tuple[WorkContextVerifier, frozenset[str], int]:
        with self._lock:
            if self._verifier is not None and self._now_unix() < self._expires_at:
                return self._verifier, self._key_ids, self._generation
            result = self._refresh_locked()
            # A scheduled refresh opens a fresh generation in which one unknown
            # key may force an early refresh for normal rotation.
            self._unknown_refresh_generation = -1
            return result

    def _refresh_unknown(self, observed_generation: int) -> WorkContextVerifier:
        with self._lock:
            if self._verifier is not None and self._generation != observed_generation:
                return self._verifier
            if self._verifier is not None and self._unknown_refresh_generation == self._generation:
                return self._verifier
            # Reserve this generation before I/O so a failed rotation refresh
            # cannot be retried on every attacker-chosen key id.
            self._unknown_refresh_generation = self._generation
            verifier, _, generation = self._refresh_locked()
            self._unknown_refresh_generation = generation
            return verifier

    def _refresh_locked(self) -> tuple[WorkContextVerifier, frozenset[str], int]:
        try:
            document = self._fetch()
        except WorkContextError:
            raise
        except Exception as exc:  # any transport failure fails closed
            raise WorkContextError(f"fetch Work Context JWKS: {exc}") from exc
        keys = parse_jwks(document)
        verifier = WorkContextVerifier(keys, clock_skew=self._clock_skew, now=self._now)
        self._verifier = verifier
        self._keys = keys
        self._key_ids = frozenset(keys)
        self._expires_at = self._now_unix() + self._cache_ttl
        self._generation += 1
        return verifier, self._key_ids, self._generation


def _token_key_id(encoded: str) -> str:
    """Peek at ``key_id`` to decide whether a refresh is warranted. Lenient on
    purpose (no canonical-base64 check): a malformed token fails in ``verify``
    without ever causing I/O."""
    validate_token_shape(encoded)
    segment = encoded.split(".", 1)[0]
    try:
        raw = segment.encode("ascii")
        payload = base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)
        probe = json.loads(payload)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, ValueError) as exc:
        raise WorkContextError(f"malformed token payload: {exc}") from exc
    key_id = probe.get("key_id") if isinstance(probe, dict) else None
    if not isinstance(key_id, str) or key_id.strip() == "":
        raise WorkContextError("key_id is required")
    if len(key_id.encode("utf-8")) > _MAX_KID_BYTES:
        raise WorkContextError(f"key_id exceeds {_MAX_KID_BYTES} bytes")
    return key_id


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise WorkContextError("Work Context JWKS redirected")


def http_fetcher(url: str, *, timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS) -> Fetcher:
    """A stdlib ``urllib`` fetcher for :class:`JWKSKeySource` with sdk-go's
    guards: absolute ``http(s)`` URL without credentials, query, or fragment;
    no redirects; HTTP 200 with ``application/json``; at most 256 KiB."""
    parsed = urllib.parse.urlsplit(url.strip())
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise WorkContextError(
            "Work Context JWKS URL must be an absolute HTTP(S) URL without credentials, query, or fragment"
        )
    if timeout <= 0 or timeout > MAX_REQUEST_TIMEOUT_SECONDS:
        raise WorkContextError(
            f"JWKS request timeout must be between 0 and {MAX_REQUEST_TIMEOUT_SECONDS}s"
        )
    endpoint = urllib.parse.urlunsplit(parsed)
    opener = urllib.request.build_opener(_NoRedirect())

    def fetch() -> bytes:
        request = urllib.request.Request(endpoint, headers={"Accept": "application/json"})
        try:
            with opener.open(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise WorkContextError(f"Work Context JWKS returned HTTP {status}")
                content_type = response.headers.get("Content-Type", "")
                if (
                    content_type
                    and content_type.split(";", 1)[0].strip().lower() != "application/json"
                ):
                    raise WorkContextError("Work Context JWKS is not application/json")
                body = response.read(MAX_JWKS_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise WorkContextError(f"Work Context JWKS returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise WorkContextError(f"fetch Work Context JWKS: {exc.reason}") from exc
        if len(body) > MAX_JWKS_BYTES:
            raise WorkContextError(f"Work Context JWKS exceeds {MAX_JWKS_BYTES} bytes")
        return body

    return fetch
