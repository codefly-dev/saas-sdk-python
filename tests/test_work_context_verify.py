"""Work Context verifier tests: the wire golden proves byte-for-byte parity with
sdk-go, the rest pin the structural, temporal, and scope semantics."""

from __future__ import annotations

import base64
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from saas_sdk import work_context as wc

_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "work_context_wire_golden.json").read_text()
)
_KEY_ID = _FIXTURE["key_id"]
_TIME = datetime.fromtimestamp(_FIXTURE["verify_time_unix"], tz=timezone.utc)


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _private_key(seed: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(seed)


def _public_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def _golden_public_key() -> bytes:
    seed = bytes.fromhex(_FIXTURE["signing_key_seed_hex"])
    return _public_bytes(_private_key(seed))


def _fixed_now(unix: int) -> wc._NowFn:
    moment = datetime.fromtimestamp(unix, tz=timezone.utc)
    return lambda: moment


def _canonical_payload(**overrides) -> dict:
    """A fresh, canonical payload matching the golden input. Sign it to mint a
    valid token for a chosen key without an authority-side signer."""
    payload = {
        "typ": wc.WORK_CONTEXT_TYPE,
        "algorithm": wc.WORK_CONTEXT_ALGORITHM,
        "key_id": _KEY_ID,
        "issuer": "https://accounts.codefly.dev/work-context",
        "audience": "warden.evidence",
        "not_before_unix": _FIXTURE["verify_time_unix"],
        "issued_at_unix": _FIXTURE["verify_time_unix"],
        "expires_at_unix": _FIXTURE["verify_time_unix"] + 300,
        "nonce": "nonce-fixed-for-golden",
        "authorization_revision": "42",
        "replay_policy": "idempotent",
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
        "actor_chain": [],
        "attribution_team_ids": ["team-ai", "team-platform"],
    }
    payload.update(overrides)
    return payload


def sign_token(payload: dict, seed: bytes) -> str:
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    signature = _private_key(seed).sign(payload_bytes)
    return _b64url_encode(payload_bytes) + "." + _b64url_encode(signature)


def golden_verifier(now: int | None = None) -> wc.Verifier:
    return wc.Verifier(
        {_KEY_ID: _golden_public_key()},
        now=_fixed_now(_FIXTURE["verify_time_unix"] if now is None else now),
    )


# --- wire golden ---------------------------------------------------------------


def test_wire_golden_verifies_and_reports_expected_claims():
    """The exact bytes sdk-go emits must verify here and decode to the same
    canonicalized claims — the cross-language wire-parity proof."""
    claims = golden_verifier().verify(
        _FIXTURE["token"], wc.Expectations(**_FIXTURE["expectations"])
    )

    expected = _FIXTURE["expected_claims"]
    assert claims.authorization_revision == expected["authorization_revision"] == (1 << 64) - 1
    assert claims.nonce == "nonce-fixed-for-golden"
    assert claims.parent_session_id is None
    assert claims.workspace_id == "workspace-deus"
    assert claims.project_id == "project-warden"
    assert claims.attribution_team_ids == ("team-ai", "team-platform")
    assert [s.resource_kind for s in claims.authority_scopes] == ["evidence", "repository"]
    assert claims.authority_scopes[1].actions == ("read", "write")
    assert claims.authority_scopes[1].resource_ids == ("repo-codefly", "repo-warden")
    assert claims.actor_chain[0].principal_id == "agent-claude-code"
    assert claims.actor_chain[0].granted_scopes[1].resource_ids == ("repo-warden",)


def test_wire_golden_payload_matches_fixture_claims_field_by_field():
    """Decode the golden payload directly and confirm every field, so a silent
    re-encoding drift in either SDK is caught."""
    payload_segment = _FIXTURE["token"].split(".", 1)[0]
    decoded = json.loads(_b64url_decode(payload_segment))
    expected = dict(_FIXTURE["expected_claims"])
    # The wire payload carries authorization_revision as a decimal string and
    # omits absent optional fields; normalize before comparing to claim values.
    assert decoded["authorization_revision"] == str(expected["authorization_revision"])
    assert "parent_session_id" not in decoded
    decoded["authorization_revision"] = int(decoded["authorization_revision"])
    decoded["parent_session_id"] = None
    assert decoded == expected


def test_public_key_derivation_matches_fixture():
    assert _b64url_encode(_golden_public_key()) == _FIXTURE["public_key_b64url"]


# --- signature & key selection -------------------------------------------------


def test_rejects_tampered_payload():
    payload_segment, signature_segment = _FIXTURE["token"].split(".", 1)
    payload = bytearray(_b64url_decode(payload_segment))
    payload[len(payload) // 2] ^= 1
    forged = _b64url_encode(bytes(payload)) + "." + signature_segment
    with pytest.raises(wc.WorkContextError, match="signature"):
        golden_verifier().verify(forged)


def test_rejects_unknown_key_id():
    token = sign_token(_canonical_payload(key_id="other-key"), bytes(range(32)))
    with pytest.raises(wc.WorkContextError, match="unknown key id"):
        golden_verifier().verify(token)


def test_rejects_wrong_signing_key():
    token = sign_token(_canonical_payload(), bytes(range(1, 33)))
    with pytest.raises(wc.WorkContextError, match="signature"):
        golden_verifier().verify(token)


# --- expectation matching ------------------------------------------------------


@pytest.mark.parametrize(
    "expectations",
    [
        wc.Expectations(audience="other-service"),
        wc.Expectations(tenant_id="tenant-mind"),
        wc.Expectations(owner_principal_id="principal-other"),
        wc.Expectations(task_id="task-other"),
        wc.Expectations(session_id="session-other"),
        wc.Expectations(issuer="https://evil.example/work-context"),
    ],
)
def test_rejects_expectation_mismatch(expectations):
    with pytest.raises(wc.WorkContextError, match="mismatch"):
        golden_verifier().verify(_FIXTURE["token"], expectations)


def test_authorization_revision_expectation():
    with pytest.raises(wc.WorkContextError, match="authorization revision mismatch"):
        golden_verifier().verify(_FIXTURE["token"], wc.Expectations(authorization_revision=1))
    claims = golden_verifier().verify(
        _FIXTURE["token"], wc.Expectations(authorization_revision=(1 << 64) - 1)
    )
    assert claims.authorization_revision == (1 << 64) - 1


# --- time window ---------------------------------------------------------------


def test_rejects_expired_token():
    with pytest.raises(wc.WorkContextError, match="expired"):
        golden_verifier(now=_FIXTURE["verify_time_unix"] + 7 * 60).verify(_FIXTURE["token"])


def test_rejects_not_yet_active_token():
    seed = bytes(range(32))
    future = _FIXTURE["verify_time_unix"] + 120
    token = sign_token(_canonical_payload(not_before_unix=future, expires_at_unix=future + 300), seed)
    verifier = wc.Verifier({_KEY_ID: _public_bytes(_private_key(seed))}, now=_fixed_now(_FIXTURE["verify_time_unix"]))
    with pytest.raises(wc.WorkContextError, match="not active"):
        verifier.verify(token)


def test_clock_skew_tolerates_bounded_drift():
    # 45s past expiry is inside the default one-minute skew.
    golden_verifier(now=_FIXTURE["verify_time_unix"] + 345).verify(_FIXTURE["token"])


def test_rejects_excessive_lifetime():
    seed = bytes(range(32))
    now = _FIXTURE["verify_time_unix"]
    token = sign_token(_canonical_payload(expires_at_unix=now + 16 * 60), seed)
    verifier = wc.Verifier({_KEY_ID: _public_bytes(_private_key(seed))}, now=_fixed_now(now))
    with pytest.raises(wc.WorkContextError, match="lifetime"):
        verifier.verify(token)


# --- structural validation -----------------------------------------------------


def _verify_local(payload: dict, seed: bytes = bytes(range(32))):
    token = sign_token(payload, seed)
    verifier = wc.Verifier({payload["key_id"]: _public_bytes(_private_key(seed))}, now=_fixed_now(_FIXTURE["verify_time_unix"]))
    return verifier.verify(token)


@pytest.mark.parametrize("field", ["parent_session_id", "workspace_id", "project_id"])
def test_rejects_present_but_empty_optional_field(field):
    """The proto declares min_len=1 on these optional fields (codefly-dev/sdk-go#7);
    present-but-empty must fail closed."""
    with pytest.raises(wc.WorkContextError):
        _verify_local(_canonical_payload(**{field: ""}))


@pytest.mark.parametrize("field", ["parent_session_id", "workspace_id", "project_id"])
def test_accepts_present_non_empty_optional_field(field):
    value = "session-other" if field == "parent_session_id" else "value"
    claims = _verify_local(_canonical_payload(**{field: value}))
    assert getattr(claims, field) == value


def test_whitespace_only_required_field_is_accepted():
    """min_len=1 is a byte-length floor, not a trim: a non-empty whitespace id
    (" ") clears it and must be accepted, so Python never rejects a token sdk-go
    accepts (finding #3). Only a genuinely empty required id is rejected."""
    claims = _verify_local(_canonical_payload(tenant_id=" "))
    assert claims.tenant_id == " "

    with pytest.raises(wc.WorkContextError, match="tenant_id is required"):
        _verify_local(_canonical_payload(tenant_id=""))


def test_rejects_unknown_payload_field():
    with pytest.raises(wc.WorkContextError, match="unknown payload field"):
        _verify_local(_canonical_payload(extra="nope"))


def test_rejects_unknown_scope_field():
    payload = _canonical_payload()
    payload["authority_scopes"][0]["surprise"] = 1
    with pytest.raises(wc.WorkContextError, match="unknown scope field"):
        _verify_local(payload)


def test_rejects_bad_typ_and_algorithm():
    with pytest.raises(wc.WorkContextError, match="typ"):
        _verify_local(_canonical_payload(typ="jwt"))
    with pytest.raises(wc.WorkContextError, match="algorithm"):
        _verify_local(_canonical_payload(algorithm="HS256"))


def test_rejects_unsupported_replay_policy():
    with pytest.raises(wc.WorkContextError, match="replay policy"):
        _verify_local(_canonical_payload(replay_policy="reusable"))


def test_rejects_unsorted_scopes():
    payload = _canonical_payload()
    payload["authority_scopes"].reverse()
    with pytest.raises(wc.WorkContextError, match="sorted and unique"):
        _verify_local(payload)


def test_rejects_unsorted_attribution_team_ids():
    with pytest.raises(wc.WorkContextError, match="sorted and unique"):
        _verify_local(_canonical_payload(attribution_team_ids=["team-platform", "team-ai"]))


def test_rejects_parent_session_equal_to_session():
    with pytest.raises(wc.WorkContextError, match="parent session equals session"):
        _verify_local(_canonical_payload(parent_session_id="session-root"))


def test_authorization_revision_must_be_decimal_string():
    payload = _canonical_payload()
    payload["authorization_revision"] = 42  # a JSON number, not the decimal string
    with pytest.raises(wc.WorkContextError, match="authorization_revision"):
        _verify_local(payload)


def test_authorization_revision_rejects_overflow():
    with pytest.raises(wc.WorkContextError, match="authorization_revision"):
        _verify_local(_canonical_payload(authorization_revision=str(1 << 64)))


def test_authorization_revision_overlong_fails_as_work_context_error():
    """A digit string past CPython's int-conversion limit must surface as a
    WorkContextError, not a raw ValueError escaping the verifier (finding #2)."""
    with pytest.raises(wc.WorkContextError, match="authorization_revision"):
        _verify_local(_canonical_payload(authorization_revision="9" * 5000))


def test_authorization_revision_accepts_leading_zeros_like_go():
    """Go's ParseUint accepts leading zeros; the verifier must too, even for a
    string longer than the int-conversion limit that normalizes to zero."""
    claims = _verify_local(_canonical_payload(authorization_revision="0" * 5000))
    assert claims.authorization_revision == 0


# --- actor chain attenuation ---------------------------------------------------


def _actor(scopes):
    return {
        "principal_id": "agent-claude-code",
        "principal_kind": "agent",
        "delegation_id": "delegation-1",
        "granted_scopes": scopes,
    }


def test_accepts_attenuating_actor_chain():
    payload = _canonical_payload(
        actor_chain=[
            _actor(
                [
                    {"resource_kind": "evidence", "actions": ["append"], "resource_ids": []},
                    {"resource_kind": "repository", "actions": ["read"], "resource_ids": ["repo-warden"]},
                ]
            )
        ]
    )
    claims = _verify_local(payload)
    assert claims.effective_scopes()[1].actions == ("read",)


@pytest.mark.parametrize(
    "granted",
    [
        [{"resource_kind": "repository", "actions": ["admin"], "resource_ids": ["repo-warden"]}],
        [{"resource_kind": "repository", "actions": ["read"], "resource_ids": ["repo-mind"]}],
        [{"resource_kind": "repository", "actions": ["read"], "resource_ids": []}],
        [{"resource_kind": "secrets", "actions": ["read"], "resource_ids": []}],
    ],
)
def test_rejects_scope_widening_actor(granted):
    with pytest.raises(wc.WorkContextError, match="widens authority"):
        _verify_local(_canonical_payload(actor_chain=[_actor(granted)]))


# --- require_scope -------------------------------------------------------------


def test_require_scope_grants_and_denies():
    claims = golden_verifier().verify(_FIXTURE["token"])
    # effective scope is the actor's granted scopes.
    wc.require_scope(claims, wc.ScopeRequirement("repository", "write", "repo-warden"))
    wc.require_scope(claims, wc.ScopeRequirement("evidence", "append"))
    with pytest.raises(wc.WorkContextDenied):
        wc.require_scope(claims, wc.ScopeRequirement("repository", "write", "repo-codefly"))
    with pytest.raises(wc.WorkContextDenied):
        wc.require_scope(claims, wc.ScopeRequirement("repository", "admin", "repo-warden"))


def test_require_scope_wildcard_and_explicit():
    claims = golden_verifier().verify(_FIXTURE["token"])
    # evidence has no resource_ids: wildcard grants any resource unless explicit.
    wc.require_scope(claims, wc.ScopeRequirement("evidence", "append", "anything"))
    # require_explicit_resource declines a wildcard scope: the explicit id is not
    # in evidence's (empty) resource_ids, so the grant is denied.
    with pytest.raises(wc.WorkContextDenied):
        wc.require_scope(
            claims,
            wc.ScopeRequirement("evidence", "append", "anything", require_explicit_resource=True),
        )


def test_require_scope_revalidates_mutated_claims():
    claims = golden_verifier().verify(_FIXTURE["token"])
    mutated = copy.deepcopy(claims)
    # Break canonical action sorting; require_scope must fail closed, not authorize.
    object.__setattr__(mutated.actor_chain[0].granted_scopes[1], "actions", ("write", "read"))
    with pytest.raises(wc.WorkContextError):
        wc.require_scope(mutated, wc.ScopeRequirement("repository", "read", "repo-warden"))


# --- malformed tokens ----------------------------------------------------------


@pytest.mark.parametrize("encoded", ["", "one-segment", "a.b.c", "!!!.!!!", "abc.def"])
def test_malformed_tokens_fail_closed(encoded):
    with pytest.raises(wc.WorkContextError):
        golden_verifier().verify(encoded)


def test_rejects_non_canonical_base64():
    _, signature_segment = _FIXTURE["token"].split(".", 1)
    # "AB" decodes to one zero byte but re-encodes to "AA": its trailing bits are
    # non-zero, so it is not canonical base64url and must be rejected.
    with pytest.raises(wc.WorkContextError, match="canonical"):
        golden_verifier().verify("AB." + signature_segment)


def test_rejects_oversized_token():
    with pytest.raises(wc.WorkContextError, match="exceeds"):
        golden_verifier().verify("a" * (32 * 1024 + 1) + "." + "b")


def test_verifier_rejects_bad_configuration():
    with pytest.raises(wc.WorkContextError, match="no public"):
        wc.Verifier({})
    with pytest.raises(wc.WorkContextError, match="32 bytes"):
        wc.Verifier({"k": b"short"})
    with pytest.raises(wc.WorkContextError, match="clock skew"):
        wc.Verifier({_KEY_ID: _golden_public_key()}, clock_skew=timedelta(minutes=2))


def test_token_from_headers():
    assert wc.token_from_headers({wc.WORK_CONTEXT_HEADER: "abc"}) == "abc"
    assert wc.token_from_headers({}) == ""
    with pytest.raises(wc.WorkContextError):
        wc.token_from_headers(None)
