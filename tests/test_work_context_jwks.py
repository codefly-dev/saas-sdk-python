"""JWKS-backed verifier tests over a real local HTTP server: caching, rotation,
the bounded unknown-key refresh, redirect rejection, and fail-closed boot."""

from __future__ import annotations

import base64
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from saas_sdk import work_context as wc
from test_work_context import _canonical_payload, sign_token

_NOW_UNIX = 1784810096


def _seed(byte: int) -> bytes:
    return bytes((byte + i) & 0xFF for i in range(32))


def _public_bytes(seed: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw
    )


def _jwks_json(keys: dict[str, bytes]) -> bytes:
    document = {
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "alg": "EdDSA",
                "use": "sig",
                "kid": key_id,
                "x": base64.urlsafe_b64encode(public).rstrip(b"=").decode(),
            }
            for key_id, public in keys.items()
        ]
    }
    return json.dumps(document).encode()


def _token(key_id: str, seed: bytes) -> str:
    return sign_token(_canonical_payload(key_id=key_id), seed)


def _now():
    moment = datetime.fromtimestamp(_NOW_UNIX, tz=timezone.utc)
    return moment


class _State:
    def __init__(self, handler):
        self.handler = handler  # () -> (status, content_type, body_bytes)
        self.requests = 0
        self.lock = threading.Lock()


def _server(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            with state.lock:
                state.requests += 1
            status, content_type, body = state.handler()
            self.send_response(status)
            if content_type is not None:
                self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    return httpd, f"http://{host}:{port}/v1/auth/.well-known/jwks.json"


def _ok(keys: dict[str, bytes]):
    return lambda: (200, "application/json", _jwks_json(keys))


def _verifier(url, **kwargs):
    return wc.JWKSVerifier(url, now=_now, **kwargs)


def test_caches_and_refreshes_on_unknown_rotation():
    keys = {"key-1": _public_bytes(_seed(1))}
    state = _State(lambda: (200, "application/json", _jwks_json(keys)))
    httpd, url = _server(state)
    try:
        verifier = _verifier(url)
        first = _token("key-1", _seed(1))
        for _ in range(3):
            claims = verifier.verify(first, wc.Expectations(audience="warden.evidence"))
            assert claims.tenant_id == "tenant-codefly"
        assert state.requests == 1  # one fetch serves the cached window

        keys.clear()
        keys["key-2"] = _public_bytes(_seed(2))
        second = _token("key-2", _seed(2))
        verifier.verify(second)
        assert state.requests == 2  # unknown key forced one rotation refresh

        # The removed key now fails, and arbitrary unknown ids cannot loop the
        # endpoint: only one unknown-key refresh is spent per cache generation.
        for index in range(50):
            with pytest.raises(wc.WorkContextError):
                verifier.verify(_token(f"unknown-{index}", _seed(1)))
        with pytest.raises(wc.WorkContextError):
            verifier.verify(first)
        assert state.requests == 2
    finally:
        httpd.shutdown()


def test_expired_cache_refetches_but_bad_signature_does_not():
    now_box = {"unix": _NOW_UNIX}
    keys = {"key-1": _public_bytes(_seed(1))}
    state = _State(lambda: (200, "application/json", _jwks_json(keys)))
    httpd, url = _server(state)
    try:
        verifier = wc.JWKSVerifier(
            url,
            now=lambda: datetime.fromtimestamp(now_box["unix"], tz=timezone.utc),
            cache_ttl=timedelta(minutes=1),
        )
        verifier.verify(_token("key-1", _seed(1)))
        assert state.requests == 1

        # A known key id with a bad signature is an invalid token, not a
        # rotation signal, and must never trigger network I/O.
        with pytest.raises(wc.WorkContextError, match="signature"):
            verifier.verify(_token("key-1", _seed(9)))
        assert state.requests == 1

        now_box["unix"] += 61
        verifier.verify(_token("key-1", _seed(1)))
        assert state.requests == 2
    finally:
        httpd.shutdown()


def test_rejects_redirects_without_following_them():
    destination_hits = {"n": 0}

    def dest_handler():
        destination_hits["n"] += 1
        return 200, "application/json", _jwks_json({"key-1": _public_bytes(_seed(1))})

    dest_httpd, dest_url = _server(_State(dest_handler))

    class SourceHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(307)
            self.send_header("Location", dest_url)
            self.send_header("Content-Length", "0")
            self.end_headers()

    src_httpd = ThreadingHTTPServer(("127.0.0.1", 0), SourceHandler)
    threading.Thread(target=src_httpd.serve_forever, daemon=True).start()
    host, port = src_httpd.server_address
    src_url = f"http://{host}:{port}/v1/auth/.well-known/jwks.json"
    try:
        verifier = _verifier(src_url)
        with pytest.raises(wc.WorkContextError):
            verifier.verify(_token("key-1", _seed(1)))
        assert destination_hits["n"] == 0
    finally:
        src_httpd.shutdown()
        dest_httpd.shutdown()


def test_refresh_fails_closed_at_boot():
    state = _State(lambda: (503, "application/json", b"{}"))
    httpd, url = _server(state)
    try:
        verifier = _verifier(url)
        with pytest.raises(wc.WorkContextError, match="HTTP 503"):
            verifier.refresh()
    finally:
        httpd.shutdown()


def test_refresh_warms_cache_for_first_verify():
    keys = {"key-1": _public_bytes(_seed(1))}
    state = _State(lambda: (200, "application/json", _jwks_json(keys)))
    httpd, url = _server(state)
    try:
        verifier = _verifier(url)
        verifier.refresh()
        assert state.requests == 1
        verifier.verify(_token("key-1", _seed(1)))
        assert state.requests == 1  # served from the warmed cache
    finally:
        httpd.shutdown()


@pytest.mark.parametrize(
    "response",
    [
        (503, "application/json", b"{}"),
        (200, "text/plain", b"{}"),
        (200, "application/json", b'{"keys":[]}'),
        (200, "application/json", b'{"keys":[{"kty":"OKP","crv":"X25519","kid":"key-1","x":"AA"}]}'),
        (200, "application/json", b'{"keys":[{"kty":"OKP","crv":"Ed25519","kid":"key-1","x":"AA"}]}'),
    ],
)
def test_rejects_malformed_or_bounded_jwks(response):
    state = _State(lambda: response)
    httpd, url = _server(state)
    try:
        verifier = _verifier(url)
        with pytest.raises(wc.WorkContextError):
            verifier.verify(_token("key-1", _seed(1)))
    finally:
        httpd.shutdown()


def test_rejects_oversized_jwks():
    body = b"x" * (256 * 1024 + 1)
    state = _State(lambda: (200, "application/json", body))
    httpd, url = _server(state)
    try:
        with pytest.raises(wc.WorkContextError, match="exceeds"):
            _verifier(url).verify(_token("key-1", _seed(1)))
    finally:
        httpd.shutdown()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "accounts.example.test/keys",
        "file:///tmp/keys.json",
        "https://user:secret@accounts.example.test/keys",
        "https://accounts.example.test/keys?tenant=codefly",
        "https://accounts.example.test/keys#fragment",
    ],
)
def test_rejects_unsafe_url(url):
    with pytest.raises(wc.WorkContextError):
        wc.JWKSVerifier(url)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cache_ttl": timedelta(milliseconds=1)},
        {"cache_ttl": timedelta(hours=25)},
        {"request_timeout": timedelta(seconds=31)},
    ],
)
def test_rejects_unsafe_timing_configuration(kwargs):
    with pytest.raises(wc.WorkContextError):
        wc.JWKSVerifier("https://accounts.example.test/keys", **kwargs)
