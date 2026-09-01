"""JWKS key discovery: the accounts document shape, and the cache / rotation
behaviour of ``JWKSKeySource`` (the twin of sdk-go's ``work_context_jwks.go``
tests, with the transport injected instead of mocked)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import (
    ISSUER,
    KID,
    TEST_TIME,
    b64url,
    canonical_payload,
    key_from_seed,
    public_bytes,
    sign,
)
from saas_sdk import jwks
from saas_sdk import work_context as wc


def jwk(kid: str, public_key: bytes, **extra) -> dict:
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "alg": "EdDSA",
        "use": "sig",
        "kid": kid,
        "x": b64url(public_key),
        **extra,
    }


def document(*keys: dict) -> dict:
    return {"keys": list(keys)}


# --------------------------------------------------------------------------- #
# parse_jwks
# --------------------------------------------------------------------------- #


def test_parse_accounts_shaped_jwks(public_key):
    # Exactly what accounts' minter publishes at /v1/auth/.well-known/jwks.json.
    keys = jwks.parse_jwks(document(jwk(KID, public_key)))
    assert keys == {KID: public_key}
    assert jwks.parse_jwks(json.dumps(document(jwk(KID, public_key)))) == keys
    assert jwks.parse_jwks(json.dumps(document(jwk(KID, public_key))).encode()) == keys


def test_parse_jwks_tolerates_absent_alg_and_use(public_key):
    entry = {"kty": "OKP", "crv": "Ed25519", "kid": KID, "x": b64url(public_key)}
    assert jwks.parse_jwks(document(entry)) == {KID: public_key}


@pytest.mark.parametrize(
    "doc, message",
    [
        ({"keys": []}, "between 1 and 64 keys"),
        ({}, "between 1 and 64 keys"),
        ("[]", "not a JSON object"),
        ("not json", "decode Work Context JWKS"),
        ({"keys": "nope"}, "keys must be an array"),
        ({"keys": ["nope"]}, "key is not an object"),
        ({"keys": [{"kty": "RSA", "kid": "k", "n": "..", "e": "AQAB"}]}, "non-Ed25519"),
        ({"keys": [{"kty": "OKP", "crv": "X25519", "kid": "k", "x": "AA"}]}, "non-Ed25519"),
        (
            {"keys": [{"kty": "OKP", "crv": "Ed25519", "alg": "RS256", "kid": "k", "x": "AA"}]},
            "non-Ed25519",
        ),
        (
            {"keys": [{"kty": "OKP", "crv": "Ed25519", "use": "enc", "kid": "k", "x": "AA"}]},
            "non-Ed25519",
        ),
        ({"keys": [{"kty": "OKP", "crv": "Ed25519", "x": "AA"}]}, "key_id is required"),
        (
            {"keys": [{"kty": "OKP", "crv": "Ed25519", "kid": "k" * 129, "x": "AA"}]},
            "key_id exceeds 128 bytes",
        ),
        (
            {"keys": [{"kty": "OKP", "crv": "Ed25519", "kid": "k", "x": "AA"}]},
            "invalid Ed25519 public key",
        ),
        (
            {"keys": [{"kty": "OKP", "crv": "Ed25519", "kid": "k", "x": "!!!!"}]},
            "invalid Ed25519 public key",
        ),
        ({"keys": [{"kty": "OKP", "crv": "Ed25519", "kid": "k"}]}, "invalid Ed25519 public key"),
    ],
)
def test_parse_jwks_rejects_bad_documents(doc, message):
    with pytest.raises(wc.WorkContextError, match=message):
        jwks.parse_jwks(doc)


def test_parse_jwks_rejects_duplicates_and_too_many_keys(public_key):
    with pytest.raises(wc.WorkContextError, match="duplicate key ID"):
        jwks.parse_jwks(document(jwk(KID, public_key), jwk(KID, public_key)))
    with pytest.raises(wc.WorkContextError, match="between 1 and 64 keys"):
        jwks.parse_jwks(document(*(jwk(f"k{i}", public_key) for i in range(65))))
    with pytest.raises(wc.WorkContextError, match="exceeds 262144 bytes"):
        jwks.parse_jwks(b" " * (jwks.MAX_JWKS_BYTES + 1))


# --------------------------------------------------------------------------- #
# JWKSKeySource caching and rotation
# --------------------------------------------------------------------------- #


class Fetcher:
    """An injectable fetcher whose document and failure mode the test controls."""

    def __init__(self, doc):
        self.doc = doc
        self.calls = 0
        self.fail: Exception | None = None

    def __call__(self):
        self.calls += 1
        if self.fail is not None:
            raise self.fail
        return self.doc


def token_for(kid: str, seed: bytes) -> str:
    return sign(canonical_payload(key_id=kid), key_from_seed(seed))


SEED_1 = bytes(range(1, 33))
SEED_2 = bytes(range(2, 34))


def test_source_caches_and_refreshes_once_on_unknown_kid():
    fetcher = Fetcher(document(jwk("key-1", public_bytes(key_from_seed(SEED_1)))))
    source = jwks.JWKSKeySource(fetcher, now=lambda: TEST_TIME)
    first = token_for("key-1", SEED_1)
    expected = wc.WorkContextExpectations(issuer=ISSUER, audience="warden.evidence")

    for _ in range(3):
        assert source.verify(first, expected).tenant_id == "tenant-codefly"
    assert fetcher.calls == 1
    assert source.keys() == {"key-1": public_bytes(key_from_seed(SEED_1))}

    # Rotation: the document now carries only key-2; the unknown kid forces
    # exactly one refresh and the new token verifies.
    fetcher.doc = document(jwk("key-2", public_bytes(key_from_seed(SEED_2))))
    assert source.verify(token_for("key-2", SEED_2), expected).tenant_id == "tenant-codefly"
    assert fetcher.calls == 2

    # Removed keys fail after the rotation refresh, and arbitrary unknown kids
    # cannot turn verification into a request loop: one refresh per generation.
    for index in range(50):
        with pytest.raises(wc.WorkContextError):
            source.verify(token_for(f"unknown-{index}", SEED_1))
    with pytest.raises(wc.WorkContextError, match="unknown key id"):
        source.verify(first)
    assert fetcher.calls == 2


def test_source_refreshes_expired_cache_but_not_on_bad_signatures():
    now = [TEST_TIME]
    fetcher = Fetcher(document(jwk("key-1", public_bytes(key_from_seed(SEED_1)))))
    source = jwks.JWKSKeySource(fetcher, cache_ttl=60, now=lambda: now[0])

    source.verify(token_for("key-1", SEED_1))
    assert fetcher.calls == 1

    # A known kid with a wrong signature is an invalid token, not a rotation
    # signal, and must never cause I/O.
    with pytest.raises(wc.WorkContextError, match="signature verification failed"):
        source.verify(token_for("key-1", SEED_2))
    assert fetcher.calls == 1

    now[0] += 60
    source.verify(token_for("key-1", SEED_1))
    assert fetcher.calls == 2


def test_source_never_fails_open():
    fetcher = Fetcher({"keys": []})
    source = jwks.JWKSKeySource(fetcher, now=lambda: TEST_TIME)
    with pytest.raises(wc.WorkContextError, match="between 1 and 64 keys"):
        source.verify(token_for("key-1", SEED_1))

    fetcher.doc = document(jwk("key-1", public_bytes(key_from_seed(SEED_1))))
    fetcher.fail = ConnectionError("accounts is down")
    with pytest.raises(wc.WorkContextError, match="fetch Work Context JWKS: accounts is down"):
        source.verify(token_for("key-1", SEED_1))

    # Once loaded, an unknown kid whose refresh fails is an error too — and the
    # failed refresh is not retried for the rest of this generation.
    fetcher.fail = None
    source.verify(token_for("key-1", SEED_1))
    calls = fetcher.calls
    fetcher.fail = ConnectionError("accounts is down")
    with pytest.raises(wc.WorkContextError, match="accounts is down"):
        source.verify(token_for("key-2", SEED_2))
    with pytest.raises(wc.WorkContextError, match="unknown key id"):
        source.verify(token_for("key-2", SEED_2))
    assert fetcher.calls == calls + 1


def test_source_malformed_token_never_fetches():
    fetcher = Fetcher(document(jwk("key-1", public_bytes(key_from_seed(SEED_1)))))
    source = jwks.JWKSKeySource(fetcher, now=lambda: TEST_TIME)
    for encoded in [
        "",
        "one",
        "a.b.c",
        "!!!.!!!",
        b64url(b'{"key_id":""}') + ".sig",
        b64url(b"[1]") + ".sig",
    ]:
        with pytest.raises(wc.WorkContextError):
            source.verify(encoded)
    assert fetcher.calls == 0


def test_source_suppresses_concurrent_rotation_refresh():
    fetcher = Fetcher(document(jwk("key-1", public_bytes(key_from_seed(SEED_1)))))
    lock = threading.Lock()
    calls = 0
    original = fetcher.__call__

    def counted():
        nonlocal calls
        with lock:
            calls += 1
        return original()

    source = jwks.JWKSKeySource(counted, now=lambda: TEST_TIME)
    source.verify(token_for("key-1", SEED_1))
    fetcher.doc = document(jwk("key-2", public_bytes(key_from_seed(SEED_2))))

    token = token_for("key-2", SEED_2)
    barrier = threading.Barrier(20)
    failures: list[Exception] = []

    def worker():
        barrier.wait()
        try:
            source.verify(token)
        except Exception as exc:  # pragma: no cover - reported below
            failures.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == []
    assert calls == 2


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"cache_ttl": 0.5}, "cache TTL"),
        ({"cache_ttl": 24 * 3600 + 1}, "cache TTL"),
        ({"clock_skew": 61}, "clock skew"),
    ],
)
def test_source_refuses_unsafe_configuration(kwargs, message):
    fetcher = Fetcher(document(jwk("key-1", public_bytes(key_from_seed(SEED_1)))))
    with pytest.raises(wc.WorkContextError, match=message):
        source = jwks.JWKSKeySource(fetcher, now=lambda: TEST_TIME, **kwargs)
        source.verify(token_for("key-1", SEED_1))
    with pytest.raises(wc.WorkContextError, match="callable"):
        jwks.JWKSKeySource("https://accounts/jwks.json")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# http_fetcher — stdlib transport with sdk-go's guards, over a real server
# --------------------------------------------------------------------------- #


@pytest.fixture
def server():
    state = {"status": 200, "content_type": "application/json", "body": b"{}", "redirect": None}
    hits: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            hits.append(self.path)
            if state["redirect"] is not None and self.path != "/final":
                self.send_response(307)
                self.send_header("Location", state["redirect"])
                self.end_headers()
                return
            self.send_response(state["status"])
            self.send_header("content-type", state["content_type"])
            self.send_header("content-length", str(len(state["body"])))
            self.end_headers()
            self.wfile.write(state["body"])

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    host, port = httpd.server_address
    try:
        yield f"http://{host}:{port}", state, hits
    finally:
        httpd.shutdown()


def test_http_fetcher_end_to_end(server, public_key):
    base, state, hits = server
    state["body"] = json.dumps(document(jwk(KID, public_key))).encode()
    source = jwks.JWKSKeySource(
        jwks.http_fetcher(base + "/v1/auth/.well-known/jwks.json"), now=lambda: TEST_TIME
    )
    ctx = source.verify(sign(canonical_payload(), key_from_seed(bytes(range(32)))))
    assert ctx.key_id == KID
    assert hits == ["/v1/auth/.well-known/jwks.json"]


def test_from_url_is_the_sdk_go_constructor_shape(server, public_key):
    base, state, hits = server
    state["body"] = json.dumps(document(jwk(KID, public_key))).encode()
    # Construction validates the URL and bounds but performs no I/O.
    source = jwks.JWKSKeySource.from_url(
        base + "/v1/auth/.well-known/jwks.json", now=lambda: TEST_TIME
    )
    assert hits == []
    token = sign(canonical_payload(), key_from_seed(bytes(range(32))))
    for _ in range(3):
        assert source.verify(token).key_id == KID
    assert hits == ["/v1/auth/.well-known/jwks.json"], "the 5-minute cache absorbs repeats"
    for url, kwargs in (
        ("file:///tmp/keys.json", {}),
        ("https://accounts.example.test/keys", {"request_timeout": 31}),
        ("https://accounts.example.test/keys", {"cache_ttl": 0.5}),
    ):
        with pytest.raises(wc.WorkContextError):
            jwks.JWKSKeySource.from_url(url, **kwargs)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda s: s.update(status=503), "HTTP 503"),
        (lambda s: s.update(content_type="text/plain"), "not application/json"),
        (lambda s: s.update(body=b" " * (jwks.MAX_JWKS_BYTES + 1)), "exceeds"),
        (lambda s: s.update(body=b'{"keys":[]}'), "between 1 and 64 keys"),
    ],
)
def test_http_fetcher_rejects_bad_responses(server, mutate, message):
    base, state, _ = server
    mutate(state)
    fetch = jwks.http_fetcher(base + "/jwks.json")
    with pytest.raises(wc.WorkContextError, match=message):
        jwks.JWKSKeySource(fetch, now=lambda: TEST_TIME).verify(token_for(KID, bytes(range(32))))


def test_http_fetcher_rejects_redirects(server, public_key):
    base, state, hits = server
    state["body"] = json.dumps(document(jwk(KID, public_key))).encode()
    state["redirect"] = base + "/final"
    with pytest.raises(wc.WorkContextError, match="redirected"):
        jwks.http_fetcher(base + "/jwks.json")()
    assert hits == ["/jwks.json"], "the redirect target must never be fetched"


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
def test_http_fetcher_rejects_unsafe_urls(url):
    with pytest.raises(wc.WorkContextError, match="absolute HTTP"):
        jwks.http_fetcher(url)


def test_http_fetcher_bounds_the_timeout():
    with pytest.raises(wc.WorkContextError, match="timeout"):
        jwks.http_fetcher("https://accounts.example.test/keys", timeout=31)
