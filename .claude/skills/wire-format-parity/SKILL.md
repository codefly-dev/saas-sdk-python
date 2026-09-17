---
name: wire-format-parity
description: Change anything covered by a fixture shared byte-for-byte with saas-sdk-go — the Work Context token encoding (tests/fixtures/work_context_wire_golden.json) or the authorization-revision projection (tests/fixtures/authorization_revision_projection.json). Use when a golden test fails, when a claim, scope or payload field is added or renamed, or before editing either fixture for any reason.
---

# Changing something the Go SDK also implements

Two fixtures in `tests/fixtures/` are byte-identical to files in
[`saas-sdk-go`](https://github.com/codefly-dev/saas-sdk-go), and CI in both
repos asserts against the same bytes:

| here | there |
| --- | --- |
| `work_context_wire_golden.json` | `TestWorkContextWireGolden` |
| `authorization_revision_projection.json` | `authorizationrevision/testdata/projection.json` |

They exist so the two implementations cannot drift without a test going red.
That makes a red golden test **informative**, not an obstacle.

## If a golden test fails

Do not touch the fixture first. The failure means this implementation no longer
produces (or accepts) the bytes the Go one does, and exactly one of the two is
wrong.

1. Find which side moved. `git log -- tests/fixtures/` and the recent diff in
   `src/saas_sdk/work_context.py` usually answer it in one read.
2. If this SDK moved, fix the code here. The encoding is pinned in detail —
   field order, `uint64` carried as a decimal *string*, scope canonicalization,
   base64url without padding, `key_id` *inside* the payload rather than in a
   header. The token is **not** a JWT; do not reach for a JWT library to
   "normalise" it.
3. If the Go SDK moved, the fix belongs there, and this is a cross-repo change:
   one pull request in each repo, each naming the other, landing together.

Editing the fixture so the local suite goes green, without the matching change
in `saas-sdk-go`, is a hack in the sense the root `AGENTS.md` means: it removes
the only signal that the two implementations disagree, and the disagreement
survives in production, where one side mints what the other rejects.

## Adding a field to the wire format

The payload is closed: `_reject_unknown` in `src/saas_sdk/work_context.py`
rejects any key the verifier does not know, so a field added on the Go side and
not here is not ignored — it is a hard verification failure for every token that
carries it. Sequence it deliberately: verifier support ships and is deployed
before anything mints the new field.

A new field needs, in the same change: parsing in `_unmarshal`, structural
validation in `_validate_work_context` (including the proto's `min_len`
constraints for optional fields), the mint side if a caller sets it, and the
regenerated `work_contexts_pb2` if it is new in the proto (see
`regenerate-bindings`).

## Regenerating a fixture

Only after the Go side is agreed. Copy the file from `saas-sdk-go` verbatim
rather than re-emitting it here — the point of the fixture is that the bytes
came from the other implementation. Then run `python -m pytest -q` and confirm
the golden test verifies the copied token against the copied public key;
`test_wire_golden_payload_matches_fixture_claims_field_by_field` checks the
decoded payload field by field, so a fixture that merely parses still fails if a
claim changed meaning.

Say in the pull request body which Go commit the fixture was taken from, and
whether the paired Go pull request has landed.
