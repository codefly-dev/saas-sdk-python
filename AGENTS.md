# saas-sdk-python — agent instructions

This repo is the **Python SDK for the saas accounts API**, the twin of
[`saas-sdk-go`](https://github.com/codefly-dev/saas-sdk-go): a versioned,
published client that solutions depend on instead of regenerating their own
bindings. `README.md` documents the SDK for the people consuming it; this file
is how to work *in* the repo.

## What this repo owns — and does not

- **Owns:** the generated message bindings (`saas_sdk._gen`); the gateway-bound
  `datasource` facade; the consumer-side halves of Work Context — the mint
  client and the verifier (`saas_sdk.work_context`); the current-revision client
  (`saas_sdk.authorization_revision`).
- **Does not own:** the protos, which live in `module-saas-starter`
  (`module/services/accounts/proto`); the Connect transport, which the solution
  runtime owns behind `Gateway.unary`; the Work Context *signer*, which stays
  authority-side in `sdk-go`; the wire format, which is pinned to `sdk-go`.
- **Never hand-edit `src/saas_sdk/_gen/`.** It is regenerated from a proto ref
  recorded in `SOURCE.txt` — see the `regenerate-bindings` skill.
- Everything ships under the single top-level package `saas_sdk`, so installing
  it never claims a generic name in a consumer's import namespace. A new module
  goes inside that package, never beside it.
- The runtime takes **no** dependency on this SDK. If a change here would
  require one, the change is in the wrong repo.

## Build and test

Transcribed from `.github/workflows/ci.yml`, which runs the matrix Python
**3.10** and **3.12** on every pull request:

```bash
python -m pip install --upgrade pip
pip install -e ".[test,revision-connect,revision-grpc]"
python -m pytest -q
```

Both networking extras are installed deliberately. `revision-connect` (httpx)
and `revision-grpc` (grpcio) are optional for consumers but not for the suite:
the tests import `grpc` and `httpx` at module scope, so a missing extra fails
collection loudly instead of quietly skipping the transport tests. There are no
`skipif` markers in `tests/` — keep it that way.

Two floors move together and are not independently adjustable:
`requires-python = ">=3.10"` in `pyproject.toml`, and `protobuf>=5.29.3`, which
is the gencode line the bindings are generated with (`buf.gen.yaml` pins the
plugins to `v29.3`). Raising one without the other makes the published SDK
uninstallable for consumers still on protobuf 5.x.

## Parity with saas-sdk-go is a cross-repo invariant

Two fixtures are byte-identical to their Go counterparts, and CI in both repos
verifies the same bytes:

- `tests/fixtures/work_context_wire_golden.json` ↔ sdk-go's
  `TestWorkContextWireGolden`. The wire format is **not** a JWT; field order,
  `uint64`-as-decimal-string encoding, scope canonicalization, base64url and
  Ed25519 signing are pinned byte-for-byte.
- `tests/fixtures/authorization_revision_projection.json` ↔ the Go SDK's
  `authorizationrevision/testdata/projection.json`.

Editing a fixture to make a test here pass is not a fix — it is a silent break
of the other implementation, which will keep minting or verifying the old bytes.
A wire change is one coordinated pair of pull requests. See the
`wire-format-parity` skill.

## When something does not work

These are the fleet's rules, not this repo's, and they are stated here because
an agent reads this file and not the tracker:
https://github.com/obin-ai/handbook/issues/68.

- **A gap in the tooling is a bug in the tooling** — never a reason to reach
  around it. Not as a "workaround", not "just this once", not "until the verb
  lands". A missing capability in `codefly`, `buf` or the generation scripts is
  an issue against the thing that owns it.
- **Never hack. Always provide the best fix, even when it spans repos.** The
  right fix living in `module-saas-starter`, `sdk-go` or the solution runtime is
  not a reason to work around it here — open the pull request there. When it
  genuinely cannot be fixed now, the deliverable is a precise issue against the
  owner plus a stopgap that says in the code and in the pull request body that
  it is one. Never an unlabelled one.
- **Classify every change that makes something work**, in the pull request body:
  a *fix* at the place that owns the behaviour, or a *hack*. A hack does not
  become a fix by working, by being small, by being local, or by the real fix
  belonging elsewhere.
- **Never hardcode what the system resolves.** This SDK exists to be the thing
  that resolves. `datasource.new(gateway)` routes through the runtime's
  `Gateway.unary` rather than typing an endpoint; `JWKSVerifier` discovers
  signing keys through the published JWKS rather than pinning a key; the
  revision client loads its credential through a caller-supplied async callback
  rather than reading one out of another component's config. A literal endpoint,
  token, port or key in this package is a defect, and a test fixture that needs
  one builds it locally.
- **Diagnose, do not pattern-match.** "It started working when I set X" is not a
  diagnosis — set X back and confirm it breaks. Do not trust an error message
  before checking that it says what it appears to say. Nearly everything in
  `work_context` raises the one `WorkContextError` type, so the type discriminates
  nothing and only the message does; and `JWKSVerifier` refreshes at most once per
  cache generation on an unknown `key_id`, so a token that fails and then passes on
  a retry has told you about key rotation, not about flakiness.
- **A silent skip is a failed test.** Nothing here may pass by not running.
  Never guard a test on an optional extra being importable — install the extra
  (CI does) so the test runs or the suite fails.
- **Say what you did not verify.** Unverified is not the same as working. The
  matrix is 3.10 and 3.12; if you ran one interpreter, or could not exercise a
  transport, the pull request body says so in as many words.

## Procedures

Step-by-step procedures live in `.claude/skills/`, read only when the task needs
them rather than carried here:

<!-- skills -->
- `regenerate-bindings` — regenerating `src/saas_sdk/_gen` from the accounts
  proto, including the option-stripping step and `SOURCE.txt`.
- `wire-format-parity` — changing anything covered by a fixture shared
  byte-for-byte with `saas-sdk-go`.
<!-- /skills -->

`tests/test_agent_context.py` holds that list to the directories that exist, so
a renamed or deleted skill cannot leave a pointer here aimed at nothing. It also
holds this file to its length budget.

Keep this file under ~200 lines. Context an agent needs only in one subtree
belongs in a nested `AGENTS.md` beside that subtree, and a procedure belongs in
a skill — never appended here.
