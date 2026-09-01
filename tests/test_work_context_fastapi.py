"""The FastAPI dependency: header → verified context → scope gate, with the
401 / 403 split a ported callee relies on. Skipped when the optional extra is
not installed."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import Depends, FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from conftest import AUDIENCE, ISSUER, KID, TEST_TIME  # noqa: E402
from saas_sdk import work_context as wc  # noqa: E402
from saas_sdk.work_context_fastapi import WorkContextAuth  # noqa: E402


@pytest.fixture
def client(public_key):
    verifier = wc.WorkContextVerifier({KID: public_key}, now=lambda: TEST_TIME)
    auth = WorkContextAuth(verifier, audience=AUDIENCE, issuer=ISSUER)
    app = FastAPI()

    @app.get("/whoami")
    def whoami(ctx: wc.WorkContext = Depends(auth)):
        actor = ctx.current_actor
        return {"owner": ctx.owner_principal_id, "actor": actor.principal_id if actor else None}

    @app.post("/evidence")
    def append_evidence(ctx: wc.WorkContext = Depends(auth.require_scope("evidence", "append"))):
        return {"task": ctx.task_id}

    @app.post("/repos/{repo}/write")
    def write_repo(
        repo: str,
        ctx: wc.WorkContext = Depends(
            auth.require_scope("repository", "write", lambda r: r.path_params["repo"])
        ),
    ):
        return {"repo": repo, "session": ctx.session_id}

    @app.post("/admin")
    def admin(ctx: wc.WorkContext = Depends(auth.require_scope("repository", "admin"))):
        return {}

    return TestClient(app)


def headers(token: str) -> dict[str, str]:
    return {wc.HEADER_NAME: token}


def test_verified_context_reaches_the_handler(client, mint):
    response = client.get("/whoami", headers=headers(mint()))
    assert response.status_code == 200
    assert response.json() == {"owner": "principal-antoine", "actor": "agent-claude-code"}


def test_missing_header_is_401(client):
    response = client.get("/whoami")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Codefly-Work-Context"
    assert response.json()["detail"] == "invalid Work Context: missing Work Context header"


def test_duplicated_header_is_401(client, mint):
    token = mint()
    response = client.get("/whoami", headers=[(wc.HEADER_NAME, token), (wc.HEADER_NAME, token)])
    assert response.status_code == 401
    assert "duplicated Work Context header" in response.json()["detail"]


def test_starlette_multi_value_headers_expose_duplicates_to_from_headers(mint):
    from starlette.datastructures import Headers

    token = mint().encode()
    duplicated = Headers(
        raw=[(b"x-codefly-work-context", token), (b"x-codefly-work-context", token)]
    )
    with pytest.raises(wc.WorkContextError, match="duplicated Work Context header"):
        wc.from_headers(duplicated)
    assert wc.from_headers(Headers(raw=[(b"x-codefly-work-context", token)])) == token.decode()


@pytest.mark.parametrize("token", ["garbage", "a.b.c", ""])
def test_malformed_token_is_401(client, token):
    assert client.get("/whoami", headers=headers(token)).status_code == 401


def test_wrong_audience_is_403(client, mint):
    # Trusted (signature, issuer, time all good) but minted for another
    # service: the caller is authenticated, just not authorized here.
    response = client.get("/whoami", headers=headers(mint(audience="other-service")))
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Work Context audience 'other-service' is not 'warden.evidence'"
    )
    assert "WWW-Authenticate" not in response.headers


def test_wrong_issuer_is_401(client, mint):
    assert (
        client.get("/whoami", headers=headers(mint(issuer="https://evil.example"))).status_code
        == 401
    )


def test_expired_token_is_401(client, mint):
    token = mint(
        issued_at_unix=TEST_TIME - 600,
        not_before_unix=TEST_TIME - 600,
        expires_at_unix=TEST_TIME - 300,
    )
    response = client.get("/whoami", headers=headers(token))
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_scope_gate_allows_wildcard_and_explicit_resources(client, mint):
    token = mint()
    assert client.post("/evidence", headers=headers(token)).json() == {"task": "task-roadmap"}
    response = client.post("/repos/repo-warden/write", headers=headers(token))
    assert response.status_code == 200
    assert response.json() == {"repo": "repo-warden", "session": "session-root"}


def test_scope_gate_denies_with_403(client, mint):
    token = mint()
    # The owner may write repo-codefly; the current actor was only granted repo-warden.
    response = client.post("/repos/repo-codefly/write", headers=headers(token))
    assert response.status_code == 403
    assert response.json()["detail"] == "scope denied: repository:write:repo-codefly"
    assert client.post("/admin", headers=headers(token)).status_code == 403


def test_scope_gate_keeps_the_401_403_split(client, mint):
    assert client.post("/evidence", headers=headers(mint(issuer="https://evil"))).status_code == 401
    assert client.post("/evidence").status_code == 401
    # Wrong audience is a 403 before the scope is even looked at.
    assert client.post("/evidence", headers=headers(mint(audience="other"))).status_code == 403


def test_audience_is_mandatory_and_matched_by_the_dependency_not_the_verifier(public_key):
    verifier = wc.WorkContextVerifier({KID: public_key})
    with pytest.raises(ValueError, match="audience is required"):
        WorkContextAuth(verifier, audience="")
    auth = WorkContextAuth(verifier, audience="svc")
    assert auth.audience == "svc"
    assert auth.expectations == wc.WorkContextExpectations(issuer=wc.ACCOUNTS_ISSUER)


def test_jwks_source_satisfies_the_verifier_protocol(public_key, mint):
    from saas_sdk import jwks
    from conftest import b64url

    source = jwks.JWKSKeySource(
        lambda: {"keys": [{"kty": "OKP", "crv": "Ed25519", "kid": KID, "x": b64url(public_key)}]},
        now=lambda: TEST_TIME,
    )
    auth = WorkContextAuth(source, audience=AUDIENCE, issuer=ISSUER)
    app = FastAPI()

    @app.get("/")
    def root(ctx: wc.WorkContext = Depends(auth)):
        return {"tenant": ctx.tenant_id}

    assert TestClient(app).get("/", headers=headers(mint())).json() == {"tenant": "tenant-codefly"}


def test_request_is_available_to_resource_id_callables(client, mint):
    # Sanity: the callable receives the live request (path params resolved).
    assert client.post("/repos/repo-warden/write", headers=headers(mint())).status_code == 200
    assert client.post("/repos/repo-other/write", headers=headers(mint())).status_code == 403


def test_dependency_can_be_used_directly(public_key, mint):
    auth = WorkContextAuth(
        wc.WorkContextVerifier({KID: public_key}, now=lambda: TEST_TIME),
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-codefly-work-context", mint().encode())],
        "query_string": b"",
    }
    assert auth(Request(scope)).owner_principal_id == "principal-antoine"
