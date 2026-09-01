"""Work Context verifier: the contract is sdk-go v0.1.65's ``work_context.go``.

Three layers of proof: tokens minted here in Python (every shape, valid and
not); the scope semantics against the Go test cases; and the Go-minted golden
fixture under ``fixtures/`` — real ``sdk-go`` output, byte-identical to the
constant in sdk-go's own ``TestWorkContextWireGolden`` — verified end to end and
re-signed back to the same bytes.
"""

from __future__ import annotations

import base64
import dataclasses
import json
from pathlib import Path

import pytest

from conftest import (
    AUDIENCE,
    ISSUER,
    KID,
    TEST_TIME,
    b64url,
    canonical_payload,
    key_from_seed,
    marshal,
    public_bytes,
    sign,
)
from saas_sdk import work_context as wc

FIXTURE = Path(__file__).parent / "fixtures" / "work_context_go_v0_1_65.json"

# sdk-go's TestWorkContextWireGolden constant, shared with sdk-js.
SDK_GO_GOLDEN = (
    "eyJ0eXAiOiJjb2RlZmx5LndvcmstY29udGV4dC92MSIsImFsZ29yaXRobSI6IkVkMjU1MTkiLCJrZXlfaWQiOiJ3b3JrLWNvbnRleHQtdGVzdC0yMDI2LTA3IiwiaXNzdWVyIjoiaHR0cHM6Ly9hY2NvdW50cy5jb2RlZmx5LmRldi93b3JrLWNvbnRleHQiLCJhdWRpZW5jZSI6IndhcmRlbi5ldmlkZW5jZSIsIm5vdF9iZWZvcmVfdW5peCI6MTc4NDgxMDA5NiwiaXNzdWVkX2F0X3VuaXgiOjE3ODQ4MTAwOTYsImV4cGlyZXNfYXRfdW5peCI6MTc4NDgxMDM5Niwibm9uY2UiOiJub25jZS1maXhlZC1mb3ItZ29sZGVuIiwiYXV0aG9yaXphdGlvbl9yZXZpc2lvbiI6IjE4NDQ2NzQ0MDczNzA5NTUxNjE1IiwicmVwbGF5X3BvbGljeSI6ImlkZW1wb3RlbnQiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtY29kZWZseSIsIm93bmVyX3ByaW5jaXBhbF9pZCI6InByaW5jaXBhbC1hbnRvaW5lIiwidGFza19pZCI6InRhc2stcm9hZG1hcCIsInNlc3Npb25faWQiOiJzZXNzaW9uLXJvb3QiLCJhdXRob3JpdHlfc2NvcGVzIjpbeyJyZXNvdXJjZV9raW5kIjoiZXZpZGVuY2UiLCJhY3Rpb25zIjpbImFwcGVuZCJdLCJyZXNvdXJjZV9pZHMiOltdfSx7InJlc291cmNlX2tpbmQiOiJyZXBvc2l0b3J5IiwiYWN0aW9ucyI6WyJyZWFkIiwid3JpdGUiXSwicmVzb3VyY2VfaWRzIjpbInJlcG8tY29kZWZseSIsInJlcG8td2FyZGVuIl19XSwiYWN0b3JfY2hhaW4iOlt7InByaW5jaXBhbF9pZCI6ImFnZW50LWNsYXVkZS1jb2RlIiwicHJpbmNpcGFsX2tpbmQiOiJhZ2VudCIsImRlbGVnYXRpb25faWQiOiJkZWxlZ2F0aW9uLTEiLCJncmFudGVkX3Njb3BlcyI6W3sicmVzb3VyY2Vfa2luZCI6ImV2aWRlbmNlIiwiYWN0aW9ucyI6WyJhcHBlbmQiXSwicmVzb3VyY2VfaWRzIjpbXX0seyJyZXNvdXJjZV9raW5kIjoicmVwb3NpdG9yeSIsImFjdGlvbnMiOlsicmVhZCIsIndyaXRlIl0sInJlc291cmNlX2lkcyI6WyJyZXBvLXdhcmRlbiJdfV19XSwiYXR0cmlidXRpb25fdGVhbV9pZHMiOlsidGVhbS1haSIsInRlYW0tcGxhdGZvcm0iXSwid29ya3NwYWNlX2lkIjoid29ya3NwYWNlLWRldXMiLCJwcm9qZWN0X2lkIjoicHJvamVjdC13YXJkZW4ifQ"
    ".pVZhqvPljkv6SyFD9UAg_oKC4SPj4hIV1Ha0W33cCV04IeaayLDe0w8iVgbxy9wwE2AWY8dXbIMmvnVk0QQRAQ"
)


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


def test_python_minter_reproduces_sdk_go_golden(mint):
    # The test-side minter is only trustworthy if it matches Go byte for byte.
    assert mint() == SDK_GO_GOLDEN


def test_verify_happy_path_with_every_expectation(verifier, mint, expectations):
    ctx = verifier.verify(mint(), expectations)

    assert ctx.typ == wc.WORK_CONTEXT_TYPE
    assert ctx.key_id == KID
    assert ctx.issuer == ISSUER and ctx.audience == AUDIENCE
    assert (ctx.tenant_id, ctx.owner_principal_id, ctx.task_id) == (
        "tenant-codefly",
        "principal-antoine",
        "task-roadmap",
    )
    assert ctx.session_id == "session-root" and ctx.parent_session_id is None
    assert ctx.authorization_revision == 2**64 - 1, (
        "uint64 must survive the decimal-string wire form"
    )
    assert ctx.replay_policy == wc.REPLAY_IDEMPOTENT
    assert (ctx.not_before_unix, ctx.issued_at_unix, ctx.expires_at_unix) == (
        TEST_TIME,
        TEST_TIME,
        TEST_TIME + 300,
    )
    assert ctx.attribution_team_ids == ("team-ai", "team-platform")
    assert ctx.workspace_id == "workspace-deus" and ctx.project_id == "project-warden"
    assert [s.resource_kind for s in ctx.authority_scopes] == ["evidence", "repository"]
    assert ctx.authority_scopes[1] == wc.WorkScope(
        "repository", ("read", "write"), ("repo-codefly", "repo-warden")
    )
    assert ctx.current_actor is not None
    assert ctx.current_actor.principal_id == "agent-claude-code"
    assert ctx.effective_scopes == ctx.current_actor.granted_scopes


def test_verify_with_no_expectations_only_checks_trust(verifier, mint):
    assert verifier.verify(mint()).task_id == "task-roadmap"
    assert verifier.verify(mint(), wc.WorkContextExpectations()).task_id == "task-roadmap"


def test_owner_direct_context_has_no_actor(verifier, mint):
    ctx = verifier.verify(mint(actor_chain=[], workspace_id=None, project_id=None))
    assert ctx.current_actor is None
    assert ctx.effective_scopes == ctx.authority_scopes
    assert ctx.workspace_id is None and ctx.project_id is None


def test_to_dict_is_the_wire_payload(verifier, mint):
    ctx = verifier.verify(mint())
    assert ctx.to_dict() == canonical_payload()
    assert marshal(ctx.to_dict()) == wc.parse_token(mint())[0]


def test_parse_token_returns_raw_payload_and_signature(mint):
    payload, signature = wc.parse_token(mint())
    assert json.loads(payload)["key_id"] == KID
    assert len(signature) == 64


def test_null_reads_as_zero_value_like_go(verifier):
    token = sign(
        marshal(canonical_payload())
        .replace(b'"workspace_id":"workspace-deus"', b'"workspace_id":null')
        .replace(
            b'"attribution_team_ids":["team-ai","team-platform"]', b'"attribution_team_ids":null'
        ),
        key_from_seed(bytes(range(32))),
    )
    ctx = verifier.verify(token)
    assert ctx.workspace_id is None
    assert ctx.attribution_team_ids == ()


# --------------------------------------------------------------------------- #
# Expectations
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "expected, message",
    [
        (wc.WorkContextExpectations(audience="other-service"), "audience mismatch"),
        (wc.WorkContextExpectations(issuer="https://evil.example"), "issuer mismatch"),
        (wc.WorkContextExpectations(tenant_id="tenant-mind"), "tenant mismatch"),
        (wc.WorkContextExpectations(owner_principal_id="principal-other"), "owner mismatch"),
        (wc.WorkContextExpectations(task_id="task-other"), "task mismatch"),
        (wc.WorkContextExpectations(session_id="session-other"), "session mismatch"),
        (wc.WorkContextExpectations(parent_session_id="session-root"), "parent session mismatch"),
        (wc.WorkContextExpectations(authorization_revision=1), "authorization revision mismatch"),
    ],
)
def test_expectation_mismatch_is_rejected(verifier, mint, expected, message):
    with pytest.raises(wc.WorkContextError, match=message):
        verifier.verify(mint(), expected)


def test_parent_session_expectation_matches_go_pointer_semantics(verifier, mint):
    # Expected "" matches a token with no parent (Go: GetParentSessionId() == "").
    verifier.verify(mint(), wc.WorkContextExpectations(parent_session_id=""))
    child = mint(session_id="session-child", parent_session_id="session-root")
    verifier.verify(child, wc.WorkContextExpectations(parent_session_id="session-root"))
    with pytest.raises(wc.WorkContextError, match="parent session mismatch"):
        verifier.verify(child, wc.WorkContextExpectations(parent_session_id=""))


def test_authorization_revision_expectation_matches_exactly(verifier, mint):
    verifier.verify(mint(), wc.WorkContextExpectations(authorization_revision=2**64 - 1))
    verifier.verify(
        mint(authorization_revision="0"), wc.WorkContextExpectations(authorization_revision=0)
    )


# --------------------------------------------------------------------------- #
# Time window (default skew: 60s)
# --------------------------------------------------------------------------- #


def _at(public_key: bytes, now: float) -> wc.WorkContextVerifier:
    return wc.WorkContextVerifier({KID: public_key}, now=lambda: now)


def test_expired_token_is_rejected_outside_skew(public_key, mint):
    token = mint()
    _at(public_key, TEST_TIME + 300 + 59).verify(token)
    with pytest.raises(wc.WorkContextError, match="expired"):
        _at(public_key, TEST_TIME + 300 + 61).verify(token)
    with pytest.raises(wc.WorkContextError, match="expired"):
        _at(public_key, TEST_TIME + 7 * 60).verify(token)


def test_not_yet_valid_token_is_rejected_outside_skew(public_key, mint):
    token = mint(not_before_unix=TEST_TIME + 120)
    with pytest.raises(wc.WorkContextError, match="not active"):
        _at(public_key, TEST_TIME).verify(token)
    _at(public_key, TEST_TIME + 61).verify(token)


def test_issued_in_the_future_is_rejected(public_key, mint):
    token = mint(issued_at_unix=TEST_TIME + 120, expires_at_unix=TEST_TIME + 420)
    with pytest.raises(wc.WorkContextError, match="issued in the future"):
        _at(public_key, TEST_TIME).verify(token)


def test_zero_skew_is_honored_and_larger_than_a_minute_is_refused(public_key, mint):
    strict = wc.WorkContextVerifier({KID: public_key}, clock_skew=0, now=lambda: TEST_TIME + 301)
    with pytest.raises(wc.WorkContextError, match="expired"):
        strict.verify(mint())
    for skew in (-1, 61):
        with pytest.raises(wc.WorkContextError, match="clock skew"):
            wc.WorkContextVerifier({KID: public_key}, clock_skew=skew)


def test_now_may_be_a_datetime(public_key, mint):
    from datetime import datetime, timezone

    at = datetime.fromtimestamp(TEST_TIME + 10, tz=timezone.utc)
    wc.WorkContextVerifier({KID: public_key}, now=lambda: at).verify(mint())


# --------------------------------------------------------------------------- #
# Trust: keys, signatures, encoding
# --------------------------------------------------------------------------- #


def test_unknown_key_id_is_rejected(verifier, mint):
    with pytest.raises(wc.WorkContextError, match="unknown key id 'rotated-away'"):
        verifier.verify(mint(key_id="rotated-away"))


def test_missing_key_id_is_an_unknown_key(verifier, private_key):
    token = sign(marshal(canonical_payload(key_id=None)), private_key)
    with pytest.raises(wc.WorkContextError, match="unknown key id ''"):
        verifier.verify(token)


def test_tampered_payload_fails_signature(verifier, mint):
    payload_segment, signature_segment = mint().split(".")
    payload = bytearray(base64.urlsafe_b64decode(payload_segment + "=="))
    payload[len(payload) // 2] ^= 1
    forged = b64url(bytes(payload)) + "." + signature_segment
    with pytest.raises(wc.WorkContextError, match="signature verification failed"):
        verifier.verify(forged)


def test_token_signed_by_another_key_under_a_known_kid_is_rejected(verifier, other_private_key):
    with pytest.raises(wc.WorkContextError, match="signature verification failed"):
        verifier.verify(sign(canonical_payload(), other_private_key))


def test_claim_substitution_after_signing_is_rejected(verifier, mint, private_key):
    # Re-encode the same claims with a different audience but keep the old
    # signature: the signature covers the raw payload bytes.
    _, signature_segment = mint().split(".")
    swapped = b64url(marshal(canonical_payload(audience="other-service"))) + "." + signature_segment
    with pytest.raises(wc.WorkContextError, match="signature verification failed"):
        verifier.verify(swapped)


def test_signature_must_be_64_bytes(verifier, mint):
    payload_segment, _ = mint().split(".")
    with pytest.raises(wc.WorkContextError, match="signature must be 64 bytes"):
        verifier.verify(payload_segment + "." + b64url(b"\x00" * 63))


@pytest.mark.parametrize(
    "encoded", ["", "one-segment", "a.b.c", "a.b.c.d", "!!!.!!!", ".", "a.", ".b"]
)
def test_malformed_tokens_fail_closed(verifier, encoded):
    with pytest.raises(wc.WorkContextError):
        verifier.verify(encoded)


def test_oversized_token_is_rejected_before_decoding(verifier):
    with pytest.raises(wc.WorkContextError, match="exceeds 32768 bytes"):
        verifier.verify("A" * 32 * 1024 + ".B")


def test_non_ascii_token_is_rejected(verifier):
    with pytest.raises(wc.WorkContextError):
        verifier.verify("é.b")


def test_padded_segments_are_not_canonical(verifier, mint):
    payload_segment, signature_segment = mint().split(".")
    with pytest.raises(wc.WorkContextError, match="base64|canonical"):
        verifier.verify(
            payload_segment + "=" * (-len(payload_segment) % 4) + "." + signature_segment
        )
    with pytest.raises(wc.WorkContextError, match="base64|canonical"):
        verifier.verify(payload_segment + "." + signature_segment + "=")


def test_trailing_bit_variants_are_not_canonical(verifier, mint):
    # A segment whose length is not a multiple of 4 has ignored low bits in its
    # last character; a variant that decodes to the same bytes must still be
    # rejected, or the same signed payload would have many wire spellings.
    payload_segment, signature_segment = mint().split(".")
    payload = base64.urlsafe_b64decode(payload_segment + "=" * (-len(payload_segment) % 4))
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    variants = []
    for char in alphabet:
        candidate = payload_segment[:-1] + char
        if candidate == payload_segment:
            continue
        try:
            same = base64.urlsafe_b64decode(candidate + "=" * (-len(candidate) % 4)) == payload
        except ValueError:
            same = False
        if same:
            variants.append(candidate)
    assert variants, "expected at least one non-canonical spelling"
    for candidate in variants:
        with pytest.raises(wc.WorkContextError, match="not canonical base64url"):
            verifier.verify(candidate + "." + signature_segment)


def test_standard_base64_alphabet_is_rejected(verifier, mint):
    payload_segment, signature_segment = mint().split(".")
    with pytest.raises(wc.WorkContextError):
        verifier.verify(
            payload_segment + "." + signature_segment.replace("_", "/").replace("-", "+")
        )


# --------------------------------------------------------------------------- #
# Strict payload decoding
# --------------------------------------------------------------------------- #


def _raw(private_key, payload: bytes) -> str:
    return sign(payload, private_key)


def test_unknown_field_is_rejected(verifier, mint):
    with pytest.raises(wc.WorkContextError, match="unknown field 'extra'"):
        verifier.verify(mint(extra="x"))


def test_unknown_field_inside_scope_or_actor_is_rejected(verifier, mint):
    scopes = canonical_payload()["authority_scopes"]
    scopes[0]["resource_ids_extra"] = []
    with pytest.raises(wc.WorkContextError, match="unknown field 'resource_ids_extra'"):
        verifier.verify(mint(authority_scopes=scopes))
    actors = canonical_payload()["actor_chain"]
    actors[0]["role"] = "admin"
    with pytest.raises(wc.WorkContextError, match="unknown field 'role'"):
        verifier.verify(mint(actor_chain=actors))


def test_trailing_json_is_rejected(verifier, private_key):
    # Trips the key_id probe first, exactly as Go's Verify does.
    with pytest.raises(wc.WorkContextError, match="decode key id"):
        verifier.verify(_raw(private_key, marshal(canonical_payload()) + b" {}"))
    with pytest.raises(wc.WorkContextError, match="decode key id"):
        verifier.verify(_raw(private_key, marshal(canonical_payload()) + b"\n[]"))


def test_trailing_json_is_rejected_by_the_strict_decoder_too():
    with pytest.raises(wc.WorkContextError, match="decode payload"):
        wc._unmarshal(marshal(canonical_payload()) + b" {}")


def test_non_object_payload_is_rejected(verifier, private_key):
    with pytest.raises(wc.WorkContextError):
        verifier.verify(_raw(private_key, b'["key_id"]'))
    with pytest.raises(wc.WorkContextError, match="unknown key id"):
        verifier.verify(_raw(private_key, b"null"))


def test_keys_are_matched_case_sensitively(verifier, private_key):
    # Stricter than Go's encoding/json (which also accepts "Issuer"): the
    # contract is snake_case and no signer emits anything else.
    raw = marshal(canonical_payload()).replace(b'"issuer"', b'"Issuer"')
    with pytest.raises(wc.WorkContextError, match="unknown field 'Issuer'"):
        verifier.verify(_raw(private_key, raw))


@pytest.mark.parametrize(
    "revision",
    ["-1", "+1", "1.0", "1e3", "", str(2**64), "0x10", "1_000", " 1", "abc"],
)
def test_authorization_revision_must_be_uint64_decimal_string(verifier, mint, revision):
    with pytest.raises(wc.WorkContextError, match="authorization_revision must be uint64 decimal"):
        verifier.verify(mint(authorization_revision=revision))


def test_authorization_revision_as_a_json_number_is_a_type_error(verifier, mint):
    # Go and JavaScript keep the full uint64 domain only through the decimal
    # string; a bare number is the wrong JSON type, as it is for Go's decoder.
    with pytest.raises(wc.WorkContextError, match="authorization_revision must be a string"):
        verifier.verify(mint(authorization_revision=2**64 - 1))


@pytest.mark.parametrize("value", ["1784810096", 1.0, True, 2**63, -(2**63) - 1])
def test_unix_times_must_be_int64_json_numbers(verifier, mint, value):
    with pytest.raises(wc.WorkContextError, match="decode payload: issued_at_unix"):
        verifier.verify(mint(issued_at_unix=value))


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"typ": "jwt"}, "unsupported typ"),
        ({"algorithm": "RS256"}, "unsupported algorithm"),
        ({"replay_policy": "always"}, "unsupported replay policy"),
        ({"tenant_id": ""}, "tenant_id is required"),
        ({"tenant_id": "   "}, "tenant_id is required"),
        ({"audience": "a" * 513}, "audience exceeds 512 bytes"),
        # An oversized key_id can never be in the key map, so — as in Go — the
        # probe reports it as unknown before structural validation runs.
        ({"key_id": "k" * 129}, "unknown key id"),
        ({"issuer": 42}, "issuer must be a string"),
        ({"parent_session_id": "session-root"}, "parent session equals session"),
        ({"not_before_unix": TEST_TIME + 400}, "not-before is after expiry"),
        ({"issued_at_unix": TEST_TIME + 400}, "issued-at is after expiry"),
        ({"expires_at_unix": TEST_TIME}, "lifetime must be positive"),
        (
            {"expires_at_unix": TEST_TIME + 15 * 60 + 1},
            "lifetime must be positive and at most 900s",
        ),
        (
            {"attribution_team_ids": ["team-platform", "team-ai"]},
            "attribution_team_ids must be sorted",
        ),
        (
            {"attribution_team_ids": ["team-ai", "team-ai"]},
            "attribution_team_ids must be sorted and unique",
        ),
        ({"attribution_team_ids": [""]}, "attribution_team_ids is required"),
        ({"attribution_team_ids": [f"t{i:03}" for i in range(257)]}, "too many attribution teams"),
    ],
)
def test_structural_bounds_are_enforced(verifier, mint, overrides, message):
    with pytest.raises(wc.WorkContextError, match=message):
        verifier.verify(mint(**overrides))


def test_lifetime_of_exactly_fifteen_minutes_is_accepted(public_key, mint):
    _at(public_key, TEST_TIME).verify(mint(expires_at_unix=TEST_TIME + 15 * 60))


def test_empty_parent_session_id_is_accepted_like_sdk_go(verifier, mint):
    # sdk-go's validateWorkContext treats the optional ids as not-required, so
    # a present-but-empty parent_session_id passes (the proto's min_len=1 is
    # not enforced by its verifier either). Mirrored, and flagged upstream.
    ctx = verifier.verify(mint(parent_session_id=""))
    assert ctx.parent_session_id == ""
    verifier.verify(mint(parent_session_id=""), wc.WorkContextExpectations(parent_session_id=""))


def _scopes(*entries):
    return [
        {"resource_kind": kind, "actions": list(actions), "resource_ids": list(ids)}
        for kind, actions, ids in entries
    ]


@pytest.mark.parametrize(
    "authority_scopes, message",
    [
        (_scopes(("repository", ["write", "read"], [])), "actions must be sorted and unique"),
        (_scopes(("repository", ["read", "read"], [])), "actions must be sorted and unique"),
        (_scopes(("repository", [], [])), "actions must contain 1..256 entries"),
        (_scopes(("repository", ["read"], ["b", "a"])), "resource_ids must be sorted and unique"),
        (
            _scopes(("repository", ["read"], []), ("evidence", ["append"], [])),
            "resource kinds must be sorted and unique",
        ),
        (
            _scopes(("evidence", ["append"], []), ("evidence", ["read"], [])),
            "resource kinds must be sorted and unique",
        ),
        (_scopes(("", ["read"], [])), "resource_kind is required"),
        (_scopes(("k" * 129, ["read"], [])), "resource_kind exceeds 128 bytes"),
        (_scopes(*((f"kind-{i:03}", ["read"], []) for i in range(65))), "exceeds 64 scopes"),
    ],
)
def test_scope_lists_must_be_canonical(verifier, mint, authority_scopes, message):
    with pytest.raises(wc.WorkContextError, match=message):
        verifier.verify(mint(authority_scopes=authority_scopes, actor_chain=[]))


def _actor(*scopes, principal_id="actor", delegation_id="delegation-x"):
    return {
        "principal_id": principal_id,
        "principal_kind": "agent",
        "delegation_id": delegation_id,
        "granted_scopes": _scopes(*scopes),
    }


@pytest.mark.parametrize(
    "granted",
    [
        [("repository", ["admin"], ["repo-warden"])],  # new action
        [("repository", ["read"], ["repo-mind"])],  # new resource
        [("repository", ["read"], [])],  # explicit set back to wildcard
        [("secrets", ["read"], [])],  # new resource kind
    ],
)
def test_actor_that_widens_authority_is_rejected(verifier, mint, granted):
    with pytest.raises(wc.WorkContextError, match=r"actor_chain\[0\] widens authority"):
        verifier.verify(mint(actor_chain=[_actor(*granted)]))


def test_each_actor_hop_must_attenuate_the_previous_one(verifier, mint):
    first = _actor(("repository", ["read"], ["repo-warden"]), principal_id="a1", delegation_id="d1")
    wider = _actor(
        ("repository", ["read", "write"], ["repo-warden"]), principal_id="a2", delegation_id="d2"
    )
    with pytest.raises(wc.WorkContextError, match=r"actor_chain\[1\] widens authority"):
        verifier.verify(mint(actor_chain=[first, wider]))
    narrower = _actor(
        ("repository", ["read"], ["repo-warden"]), principal_id="a2", delegation_id="d2"
    )
    ctx = verifier.verify(mint(actor_chain=[first, narrower]))
    assert [a.principal_id for a in ctx.actor_chain] == ["a1", "a2"]


def test_actor_chain_depth_is_bounded(verifier, mint):
    chain = [
        _actor(("evidence", ["append"], []), principal_id=f"a{i}", delegation_id=f"d{i}")
        for i in range(17)
    ]
    with pytest.raises(wc.WorkContextError, match="actor chain exceeds depth 16"):
        verifier.verify(mint(actor_chain=chain))
    verifier.verify(mint(actor_chain=chain[:16]))


@pytest.mark.parametrize("field", ["principal_id", "principal_kind", "delegation_id"])
def test_actor_identity_fields_are_required(verifier, mint, field):
    actor = _actor(("evidence", ["append"], []))
    actor[field] = ""
    with pytest.raises(wc.WorkContextError, match=f"actor {field} is required"):
        verifier.verify(mint(actor_chain=[actor]))


# --------------------------------------------------------------------------- #
# Scope semantics (sdk-go's RequireWorkContextScope test cases)
# --------------------------------------------------------------------------- #


def test_scope_check_uses_final_actor_effective_authority(verifier, mint):
    ctx = verifier.verify(mint())

    ctx.require_scope("repository", "write", "repo-warden", require_explicit_resource=True)
    assert ctx.has_scope("repository", "write", "repo-warden")
    assert ctx.has_scope("evidence", "append", "codefly.execution"), (
        "empty resource_ids grants every resource of the kind"
    )
    assert ctx.has_scope("evidence", "append")
    assert not ctx.has_scope(
        "evidence", "append", "codefly.execution", require_explicit_resource=True
    ), "an explicit producer binding must reject wildcard authority"

    for denied in (
        ("repository", "write", "repo-codefly"),  # the owner has it, the actor does not
        ("repository", "admin", "repo-warden"),
        ("repository", "write", None),  # explicit set is never ignored
        ("deployment", "write", "prod"),
    ):
        assert not ctx.has_scope(*denied)
        with pytest.raises(wc.WorkContextDenied):
            ctx.require_scope(*denied)


def test_owner_direct_call_is_checked_against_authority_scopes(verifier, mint):
    ctx = verifier.verify(mint(actor_chain=[]))
    assert ctx.has_scope("repository", "write", "repo-codefly")
    assert wc.has_scope(ctx, "repository", "read", "repo-warden")
    assert not ctx.has_scope("repository", "write", "repo-other")


def test_denied_is_not_an_invalid_error(verifier, mint):
    ctx = verifier.verify(mint())
    with pytest.raises(wc.WorkContextDenied) as denied:
        ctx.require_scope("deployment", "write", "prod")
    assert not isinstance(denied.value, wc.WorkContextError)
    assert str(denied.value) == "deployment:write:prod"


def test_scope_check_revalidates_mutated_claims(verifier, mint):
    ctx = verifier.verify(mint())
    actor = ctx.actor_chain[0]
    unsorted = dataclasses.replace(
        actor,
        granted_scopes=(
            actor.granted_scopes[0],
            dataclasses.replace(actor.granted_scopes[1], actions=("write", "read")),
        ),
    )
    mutated = dataclasses.replace(ctx, actor_chain=(unsorted,))
    with pytest.raises(wc.WorkContextError, match="sorted and unique"):
        mutated.has_scope("repository", "read", "repo-warden")
    with pytest.raises(wc.WorkContextError, match="nil claims"):
        wc.require_scope(None, "repository", "read", "repo-warden")  # type: ignore[arg-type]


def test_scope_requirement_itself_is_bounded(verifier, mint):
    ctx = verifier.verify(mint())
    with pytest.raises(wc.WorkContextError, match="required resource_kind is required"):
        ctx.has_scope("", "read")
    with pytest.raises(wc.WorkContextError, match="required action is required"):
        ctx.has_scope("repository", "")
    with pytest.raises(wc.WorkContextError, match="required resource_id is required"):
        ctx.has_scope("repository", "read", require_explicit_resource=True)
    with pytest.raises(wc.WorkContextError, match="required resource_id exceeds 512 bytes"):
        ctx.has_scope("repository", "read", "r" * 513)


# --------------------------------------------------------------------------- #
# Verifier construction and header carrier
# --------------------------------------------------------------------------- #


def test_verifier_refuses_unsafe_key_sets(public_key):
    with pytest.raises(wc.WorkContextError, match="no public verification keys"):
        wc.WorkContextVerifier({})
    with pytest.raises(wc.WorkContextError, match="key_id is required"):
        wc.WorkContextVerifier({"": public_key})
    with pytest.raises(wc.WorkContextError, match="key_id exceeds 128 bytes"):
        wc.WorkContextVerifier({"k" * 129: public_key})
    with pytest.raises(wc.WorkContextError, match="must be 32 bytes"):
        wc.WorkContextVerifier({KID: public_key[:31]})
    with pytest.raises(wc.WorkContextError, match="must be 32 bytes"):
        wc.WorkContextVerifier({KID: "not-bytes"})  # type: ignore[dict-item]
    assert wc.WorkContextVerifier({KID: public_key}).key_ids == frozenset({KID})


def test_header_carrier_is_sdk_owned(mint):
    token = mint()
    headers: dict[str, str] = {}
    wc.attach(headers, token)
    assert headers == {"x-codefly-work-context": token}
    assert wc.from_headers(headers) == token
    assert wc.from_headers({"X-Codefly-Work-Context": token}) == token
    with pytest.raises(wc.WorkContextError, match="missing Work Context header"):
        wc.from_headers({})
    with pytest.raises(wc.WorkContextError, match="empty token"):
        wc.from_headers({wc.HEADER_NAME: ""})
    with pytest.raises(wc.WorkContextError, match="two segments"):
        wc.from_headers({wc.HEADER_NAME: "a.b.c"})
    with pytest.raises(wc.WorkContextError):
        wc.attach(headers, "")


def test_grpc_metadata_and_raw_asgi_pairs_are_carriers(mint):
    token = mint()
    grpc_metadata = (("user-agent", "grpc-python/1.6"), ("x-codefly-work-context", token))
    assert wc.from_headers(grpc_metadata) == token
    raw_asgi = [(b"host", b"lastlogin"), (b"X-Codefly-Work-Context", token.encode())]
    assert wc.from_headers(raw_asgi) == token
    with pytest.raises(wc.WorkContextError, match="missing Work Context header"):
        wc.from_headers([(b"host", b"lastlogin")])
    with pytest.raises(wc.WorkContextError, match="unreadable headers"):
        wc.from_headers([("x-codefly-work-context", 42)])


def test_duplicated_carrier_is_rejected_not_first_wins(mint):
    from http.client import HTTPMessage

    token = mint()
    # Two values, even identical ones, are invalid — never resolved first-wins.
    with pytest.raises(wc.WorkContextError, match="duplicated Work Context header"):
        wc.from_headers([("x-codefly-work-context", token), ("X-Codefly-Work-Context", token)])
    with pytest.raises(wc.WorkContextError, match="duplicated Work Context header"):
        wc.from_headers((("x-codefly-work-context", token), ("x-codefly-work-context", "a.b")))
    # A multi-value stdlib mapping exposes both through items().
    message = HTTPMessage()
    message["X-Codefly-Work-Context"] = token
    message["x-codefly-work-context"] = token
    with pytest.raises(wc.WorkContextError, match="duplicated Work Context header"):
        wc.from_headers(message)
    single = HTTPMessage()
    single["X-Codefly-Work-Context"] = token
    assert wc.from_headers(single) == token


# --------------------------------------------------------------------------- #
# Go interop: the golden fixture minted by sdk-go v0.1.65
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def go_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def test_go_fixture_is_real_sdk_go_output(go_fixture):
    # The fixture's StartTask token must be the constant sdk-go's own golden
    # test asserts; if this ever drifts, the fixture was not minted by sdk-go.
    assert go_fixture["sdk_go_version"] == "v0.1.65"
    assert go_fixture["tokens"][0]["name"] == "start_task"
    assert go_fixture["tokens"][0]["token"] == SDK_GO_GOLDEN
    assert go_fixture["public_key_x"] == b64url(public_bytes(key_from_seed(bytes(range(32)))))


@pytest.mark.parametrize("index", [0, 1, 2], ids=["start_task", "child_session", "owner_direct"])
def test_go_minted_token_verifies_in_python(go_fixture, index):
    from saas_sdk import jwks

    entry = go_fixture["tokens"][index]
    keys = jwks.parse_jwks(go_fixture["jwks"])
    verifier = wc.WorkContextVerifier(keys, now=lambda: go_fixture["now_unix"])

    ctx = verifier.verify(entry["token"], wc.WorkContextExpectations(**entry["expectations"]))

    assert ctx.to_dict() == entry["payload"], "Python must read exactly what Go wrote"
    assert ctx.key_id == go_fixture["key_id"]
    assert ctx.issuer == go_fixture["issuer"]


def test_go_minted_tokens_resign_to_identical_bytes(go_fixture):
    # Wire parity in the other direction: the Python payload layout re-signed
    # with the fixture's test key reproduces the Go token byte for byte.
    private_key = key_from_seed(base64.urlsafe_b64decode(go_fixture["private_seed"] + "=="))
    for entry in go_fixture["tokens"]:
        assert sign(entry["payload"], private_key) == entry["token"], entry["name"]


def test_go_child_session_carries_lineage_and_two_actors(go_fixture):
    from saas_sdk import jwks

    entry = go_fixture["tokens"][1]
    verifier = wc.WorkContextVerifier(
        jwks.parse_jwks(go_fixture["jwks"]), now=lambda: go_fixture["now_unix"]
    )
    ctx = verifier.verify(entry["token"])

    assert ctx.parent_session_id == "session-root" and ctx.session_id == "session-child"
    assert [a.principal_id for a in ctx.actor_chain] == ["agent-claude-code", "tool-codefly-editor"]
    assert ctx.effective_scopes == (wc.WorkScope("repository", ("write",), ("repo-warden",)),)
    assert ctx.has_scope("repository", "write", "repo-warden")
    assert not ctx.has_scope("repository", "read", "repo-warden"), (
        "the tool hop attenuated read away"
    )
    assert not ctx.has_scope("evidence", "append")
    with pytest.raises(wc.WorkContextError, match="parent session mismatch"):
        verifier.verify(
            entry["token"], wc.WorkContextExpectations(parent_session_id="session-other")
        )


def test_go_owner_direct_token_is_robin_shaped(go_fixture):
    from saas_sdk import jwks

    entry = go_fixture["tokens"][2]
    verifier = wc.WorkContextVerifier(
        jwks.parse_jwks(go_fixture["jwks"]), now=lambda: go_fixture["now_unix"]
    )
    ctx = verifier.verify(entry["token"], wc.WorkContextExpectations(audience="lastlogin"))

    assert ctx.current_actor is None
    assert ctx.replay_policy == wc.REPLAY_SINGLE_USE
    assert ctx.expires_at_unix - ctx.issued_at_unix == wc.MAX_TTL_SECONDS
    assert ctx.has_scope("robin:tasks", "execute")
    assert ctx.has_scope("robin:tasks", "execute", "task-42")
    assert not ctx.has_scope("robin:tasks", "execute", "task-42", require_explicit_resource=True)
    with pytest.raises(wc.WorkContextError, match="audience mismatch"):
        verifier.verify(entry["token"], wc.WorkContextExpectations(audience="warden.evidence"))
