"""Shared test helpers: a **test-only** Work Context minter that reproduces
sdk-go's signer byte for byte (same key derivation, same canonical JSON, same
two-segment encoding), so the Python verifier can be exercised against tokens
of every shape without shipping a signer in the SDK.

The constants match ``sdk-go/work_context_test.go`` (``workContextTestTime``,
``workContextTestKeys``, ``workContextTestInput``) so the locally minted token
is the very same one the Go golden fixture pins.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from saas_sdk import work_context as wc

# 2026-07-23T12:34:56Z — sdk-go's workContextTestTime.
TEST_TIME = 1784810096
KID = "work-context-test-2026-07"
ISSUER = "https://accounts.codefly.dev/work-context"
AUDIENCE = "warden.evidence"


def key_from_seed(seed: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_bytes(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def marshal(payload: dict[str, Any]) -> bytes:
    """Go's ``json.Marshal`` for our payloads: compact, insertion-ordered, and
    HTML-safe escapes for ``<``, ``>``, ``&``."""
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return text.encode("utf-8")


def sign(payload: dict[str, Any] | bytes, private_key: Ed25519PrivateKey) -> str:
    raw = payload if isinstance(payload, bytes) else marshal(payload)
    return b64url(raw) + "." + b64url(private_key.sign(raw))


def canonical_payload(**overrides: Any) -> dict[str, Any]:
    """sdk-go's ``workContextTestInput`` *after* canonicalization (sorted,
    de-duplicated), in the exact wire field order. Override any field; set one
    to ``None`` to drop it (the optional pointer fields are ``omitempty``)."""
    payload: dict[str, Any] = {
        "typ": wc.WORK_CONTEXT_TYPE,
        "algorithm": wc.WORK_CONTEXT_ALGORITHM,
        "key_id": KID,
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "not_before_unix": TEST_TIME,
        "issued_at_unix": TEST_TIME,
        "expires_at_unix": TEST_TIME + 5 * 60,
        "nonce": "nonce-fixed-for-golden",
        "authorization_revision": str(2**64 - 1),
        "replay_policy": wc.REPLAY_IDEMPOTENT,
        "tenant_id": "tenant-codefly",
        "owner_principal_id": "principal-antoine",
        "task_id": "task-roadmap",
        "session_id": "session-root",
        "authority_scopes": [
            {"resource_kind": "evidence", "actions": ["append"], "resource_ids": []},
            {
                "resource_kind": "repository",
                "actions": ["read", "write"],
                "resource_ids": ["repo-codefly", "repo-warden"],
            },
        ],
        "actor_chain": [
            {
                "principal_id": "agent-claude-code",
                "principal_kind": "agent",
                "delegation_id": "delegation-1",
                "granted_scopes": [
                    {"resource_kind": "evidence", "actions": ["append"], "resource_ids": []},
                    {
                        "resource_kind": "repository",
                        "actions": ["read", "write"],
                        "resource_ids": ["repo-warden"],
                    },
                ],
            }
        ],
        "attribution_team_ids": ["team-ai", "team-platform"],
        "workspace_id": "workspace-deus",
        "project_id": "project-warden",
    }
    for name, value in overrides.items():
        if value is None:
            payload.pop(name, None)
        else:
            payload[name] = value
    return payload


@pytest.fixture(scope="session")
def private_key() -> Ed25519PrivateKey:
    # Seed bytes 0..31 — sdk-go's workContextTestKeys.
    return key_from_seed(bytes(range(32)))


@pytest.fixture(scope="session")
def other_private_key() -> Ed25519PrivateKey:
    return key_from_seed(bytes(range(1, 33)))


@pytest.fixture(scope="session")
def public_key(private_key: Ed25519PrivateKey) -> bytes:
    return public_bytes(private_key)


@pytest.fixture
def verifier(public_key: bytes) -> wc.WorkContextVerifier:
    return wc.WorkContextVerifier({KID: public_key}, now=lambda: TEST_TIME)


@pytest.fixture
def mint(private_key: Ed25519PrivateKey) -> Callable[..., str]:
    """``mint(**overrides)`` → a token signed with the test key over the
    canonical test payload with those overrides applied."""

    def _mint(**overrides: Any) -> str:
        return sign(canonical_payload(**overrides), private_key)

    return _mint


@pytest.fixture
def expectations() -> wc.WorkContextExpectations:
    return wc.WorkContextExpectations(
        issuer=ISSUER,
        audience=AUDIENCE,
        tenant_id="tenant-codefly",
        owner_principal_id="principal-antoine",
        task_id="task-roadmap",
        session_id="session-root",
    )
