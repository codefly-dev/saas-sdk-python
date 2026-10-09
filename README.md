# saas-sdk-python

The **Python SDK for the saas accounts API** — the Python twin of
[`saas-sdk-go`](https://github.com/codefly-dev/saas-sdk-go). A versioned,
published client that solutions depend on instead of regenerating their own
bindings.

Everything ships under a single top-level package, `saas_sdk`, so installing it
never claims a generic name (`saas`, `buf`, `datasource`) in the consumer's
import namespace.

Packages:

- **`saas_sdk._gen`** — private; consumers reach these types through the facades
  that re-export them (see [Consuming](#consuming)). The generated protobuf
  message bindings (`*_pb2`), from
  the accounts public proto at the ref recorded in `SOURCE.txt`. Only message
  types are generated; the runtime owns the Connect transport, so there are no
  client/server stubs. The bindings embed **only** the accounts protos this SDK
  exposes (`datasource.proto`, `work_contexts.proto`) — the `buf.validate` /
  `saas.policy` custom options, the `google.api` HTTP and `codefly.runnable`
  annotations and their shared descriptors are stripped during generation,
  so this SDK never registers
  a shared proto into the global descriptor pool (which would collide with a
  sibling saas SDK). The `google.protobuf` well-known types stay runtime types.
- **`saas_sdk.datasource`** — a gateway-bound facade over those types. It names
  the Connect procedure and routes the call through the solution runtime's
  `Gateway.unary(procedure, request, response_type)` seam, so a solution connects
  a GitHub datasource collection in a few lines:

  ```python
  from saas_sdk import datasource

  ds = datasource.new(gateway)
  source = ds.add_github_source(
      org_id=org,
      repo="codefly-dev/module-saas-starter",
      paths=["docs"],
      collection="handbook",
      access_token=token,
  )
  ds.sync(org, source.id)
  ```

  `gateway` is any value exposing `unary(procedure, request, response_type)` —
  which `solution_runtime.Gateway` already satisfies. The runtime stays
  datasource-agnostic and takes **no** dependency on this SDK.
- **`saas_sdk.work_context`** — both halves of the `x-codefly-work-context`
  feature. **Mint side**, a delegated caller mints a short-lived context at turn
  start and stamps it on outgoing calls. **Callee side**, a service verifies a
  presented context. See below.

## Calling a connected source (unreleased)

The call half uses the proto from
[module-saas-starter PR #1052](https://github.com/codefly-dev/module-saas-starter/pull/1052),
head `f4ce896d954101b164c3b511cbeea555f17302f7`, recorded in `SOURCE.txt`.
This is a development PR head, **not a released host tag**. Release waits for
the accepted host tag: record its commit and regenerate before publishing.

`datasource.invoke`, `lookup`, `declare_operations` and `list_operations` also
exist on `datasource.new(gateway)`. The host holds the credential, admits the
operation's route and schemas, resolves its endpoint, records the receipt, and
audits the call as the person. An invocation supplies an operation name and
input, never a provider URL or credential. The SDK encodes input into
`input_json` and decodes `output_json`, each carrying exactly one JSON object.
It rejects non-finite input numbers and preserves integer precision through
the string payload; operation schemas still use the host's protobuf `Struct`
fields. Every call uses the existing `Gateway.unary` seam.

The following doctest uses a gateway fixture and a source already connected to
`https://example.com`. Its declared operation is `GET /invoices`; declaring it
requires the host's admin permission. Neither URL resolution nor provider
authentication belongs in the invocation:

```pycon
>>> from saas_sdk import datasource
>>> import time
>>> operation = datasource.Operation(
...     name="list_invoices", method="GET", path="/invoices", query=["limit"],
...     input={"type": "object", "additionalProperties": False,
...            "properties": {"limit": {"type": "integer"}}},
...     output={"type": "object"}, effect=datasource.Effect.READ_ONLY,
...     max_output_bytes=65536,
... )
>>> datasource.declare_operations(gateway, "org-1", "source-1", [operation])
>>> datasource.list_operations(gateway, "org-1", "source-1") == [operation]
True
>>> result = datasource.invoke(
...     gateway, "org-1", "source-1", "list_invoices", {"limit": 2},
...     effect_id="request-1", deadline=time.time() + 3.0,
... )
>>> result.output
{'invoices': [{'id': 'invoice-1'}]}
>>> result.receipt.effect_id
'request-1'
>>> datasource.lookup(gateway, "org-1", "source-1", "request-1") == result.receipt
True

```

An omitted `effect_id` gets a UUIDv7, returned on `Result.receipt.effect_id`.
For crash-safe mutation recovery, choose and persist the ID **before** invoking:
the SDK stores nothing. Same ID and identical input means host replay; changing
input under the same ID is refused by the host. Both calls reach the host: the
SDK neither deduplicates, retries, nor caches receipts locally. It adds only
`x-codefly-effect-id` through gateway call options, matching the request's ID.
The gateway forwards its Work Context unchanged; the facade never reads,
re-mints, exchanges, or sets a Work Context header.

`deadline` is an absolute Unix timestamp in **seconds**, matching the Go SDK's
absolute deadline. The remaining duration is passed to the gateway as `timeout`;
an expired or non-finite deadline is refused before dispatch.
The gateway must support the `OperationGateway` protocol:
`unary(procedure, request, response_type, *, headers=None, timeout=None)`, merge
per-call headers with its own authority, and perform one attempt. The published
`solution-runtime-python` gateway currently has only the three-argument form,
forwards the bearer only, and uses a fixed ten-second timeout. **That runtime
needs Work Context forwarding and call options before it can use this surface.**
Existing connection methods continue to use its three-argument seam. There is
no SDK transport or fallback that bypasses the runtime.

Host Connect statuses map to the Go sibling's names:

| Host response | Python value |
|---|---|
| `PermissionDenied` | raises `NotPermitted` |
| `NotFound` | raises `UnknownOperation` |
| `InvalidArgument` + `BadRequest.FieldViolation` | raises `InputError`; `.pointer` is the first violation's JSON Pointer |
| `ResourceExhausted` + `ErrorInfo{DATASOURCE_RATE_LIMITED}` | raises `RateLimited`; `.reset_at` is the host's UTC reset time, or receipt time plus `RetryInfo.retry_delay` |
| `FailedPrecondition` | raises `ProviderRefused`; `.status` is the provider status from the details, when supplied |
| `Unavailable`, `DeadlineExceeded`, `Canceled` during invocation, or a lost reply | raises `OutcomeUnknown`, retaining `.receipt` and `.effect_id` |
| Lookup answers unknown or `Unavailable` | **returns** `OutcomeUnknown`; it is not raised |

Unknown is **not failure**: the mutation may have happened. Look up the same ID
and handle the returned value explicitly. Never create a new effect ID to
recover a lost reply. `lookup` returns `Receipt | OutcomeUnknown`; use
`isinstance(value, datasource.OutcomeUnknown)` to distinguish them. Other
lookup failures still raise normally, including cancellation and deadline expiry.
`Receipt.status` is `ReceiptStatus.COMMITTED`, `REFUSED` or `UNKNOWN`, matching
the Go SDK. Absent commit time/provider status remain `None`. Missing error
details likewise remain absent (`InputError.pointer` is empty).

The host is the disclosure guard. Typed errors preserve its message verbatim,
including credential-looking strings; the SDK does not redact or repair host
disclosures. Unknown Connect statuses and incoherent HTTP/code pairs propagate
as the original gateway exception.

The host's lookup wire request contains only `effect_id`; it resolves the stored
binding under the gateway's verified tenant. The public `org_id` and `source_id`
arguments remain for Go facade parity and are not additional lookup selectors.
Receipt status strings (`committed`, `unknown`) map to `ReceiptStatus`, and the
host's RFC3339 commit-time string becomes a timezone-aware `datetime`.

## Work Context

A Work Context is a signed, delegated-authority capability carried in the
`x-codefly-work-context` header. `saas_sdk.work_context` carries the two sides a
solution needs: the **mint-side** client to the accounts authority, and the
**callee-side** verifier. Only the *signer* itself stays authority-side in
[`sdk-go`](https://github.com/codefly-dev/sdk-go).

The wire format is **not a JWT**. A token is
`base64url(JSON payload).base64url(Ed25519 sig)`, the payload is a fixed
snake_case JSON object, and `key_id` lives *inside* the payload. Field order,
`uint64`-as-decimal-string encoding, scope canonicalization, base64url, and
Ed25519 signing are pinned byte-for-byte to `sdk-go`: the wire golden in
`tests/fixtures/work_context_wire_golden.json` is byte-identical to sdk-go's
`TestWorkContextWireGolden`, and CI in both repos verifies the same token.

### Minting (delegated caller)

A solution acting on a user's behalf mints a context at turn start and stamps it
on every outgoing call, so a downstream service can verify the delegated
authority:

```python
from saas_sdk import work_context

wc = work_context.new(gateway)
parent = wc.start_task(
    bearer=user_bearer, org_id=org, task_id=task, session_id=session,
    audience="accounts",
    scopes=[work_context.WorkContextScope(resource_kind="evidence", actions=["read"])],
)
ctx = wc.exchange_audience(bearer=user_bearer, parent=parent, audience="evidence", scopes=scopes)
work_context.attach(headers, ctx)   # per outgoing request
```

Every mint RPC is owner-bound, so the user's `bearer` is passed on each call
rather than relying on the gateway's ambient service identity; the mint client
therefore needs a gateway whose `unary` takes that `bearer`. A context lives
5 minutes by default and at most 15 (`DEFAULT_TTL` / `MAX_TTL`); `renew` extends
work running past the cap. Mint failures raise `WorkContextMintError`, distinct
from a verification failure.

### Verifying (callee)

```python
from saas_sdk import work_context as wc

verifier = wc.JWKSVerifier(
    "https://accounts.codefly.dev/v1/auth/.well-known/jwks.json",
)
verifier.refresh()  # optional: fail closed at boot if key discovery is down

token = wc.token_from_headers(request.headers)
claims = verifier.verify(token, wc.Expectations(
    issuer="https://accounts.codefly.dev/work-context",
    audience="warden.evidence",
))
wc.require_scope(claims, wc.ScopeRequirement("repository", "write", "repo-warden"))
```

`JWKSVerifier` discovers Ed25519 keys through the published JWKS endpoint,
caches them, and — rotation-aware — refreshes once per cache generation on an
unknown `key_id`. `Verifier` is the same check against a fixed set of keys.
Verification enforces the two-segment shape, the signature, structural
validation (including the proto's `min_len` constraints on optional fields and
monotonic scope attenuation), the time window, and the caller's expectations,
raising `WorkContextError` (or `WorkContextDenied` from `require_scope`) on any
failure. When the key set itself cannot be fetched or read, `JWKSVerifier` raises
`WorkContextUnavailable`, a `WorkContextError` subclass, so a consumer can report
an authority outage as unavailable rather than as an invalid capability. Replay policy is reported on the claims; enforcing single-use
consumption still requires a durable replay store the caller owns.

## Current authorization revision

`saas_sdk.authorization_revision` implements Accounts' current revision protocol
for **already verified** `WorkContext` claims. It projects the owner and every
actor's original scopes, including resource IDs and revision. The consumer keeps
signature/lifetime verification, action/resource policy and public error mapping.

```python
from saas_sdk.authorization_revision import MeshGRPCClient, RevisionDenied, RevisionUnavailable

# The host:port Codefly resolved for accounts' private `rest` endpoint.
client = MeshGRPCClient(resolved_accounts_rest_address, current_internal_credential)
try:
    await client.check(verified_claims)
finally:
    await client.aclose()
```

A current host serves this RPC as cleartext HTTP/2 (h2c) multiplexed onto accounts'
private `rest` endpoint, and leaves in-cluster transport security to the service
mesh (module-saas-starter `module/INTERNAL_TRANSPORT.md`). `MeshGRPCClient` dials
that resolved `host:port` and adds no TLS; it refuses a URL, a path or credentials
in the address. Use it only where the mesh enforces mutual TLS on the hop.
`GRPCClient("https://…", …)` remains for a deployment that terminates server TLS on
accounts itself.

Install `saas-sdk-python[revision-grpc]` for either gRPC client. Where an
endpoint explicitly serves Connect, install `[revision-connect]` and select
`ConnectClient`; selecting that compatibility transport is a composition choice,
never an automatic fallback. `revision_request(claims)` needs neither networking
extra and returns the canonical generated protobuf request.

Each check loads the current internal service credential through an async callback
and makes one query. It does not cache authorization, retry, inherit environment
proxies, follow redirects or forward caller bearer tokens, cookies or Work Context
headers. One three-second budget covers credential loading, connection and the
complete response; caller cancellation propagates. The callback and any injected
fixture transport must cooperate with cancellation. `tls_context` selects verified
trust roots; TLS verification cannot be disabled. Connect's explicit `transport`
injection exists for fixtures and is trusted to implement its own transport
security; production should use the default transport.

Only gRPC `PermissionDenied`/`FailedPrecondition`, or their coherent Connect
status/code pairs, raise `RevisionDenied`. Credential, transport and malformed
response failures raise `RevisionUnavailable`. Responses must be the canonical
empty message, and error strings omit remote details and credentials. Neither
error grants authority; consumers explicitly map them onto their public API.

The projection fixture at `tests/fixtures/authorization_revision_projection.json`
is shared byte-for-byte with the Go SDK's
`authorizationrevision/testdata/projection.json`. Owner/actor scope projection is
therefore verified independently of transport and consumer policy.

## Versioning

This SDK's release version tracks the **saas-starter module version**
(`module/module.package.codefly.yaml`), recorded in `SOURCE.txt` alongside the
proto ref the bindings were generated from. The `protobuf` runtime floor is
`>=5.29.3` (the gencode line the bindings are built with), so the SDK installs
alongside consumers still on protobuf 5.x.

## Regenerating

The proto source of truth is `module-saas-starter/module/services/accounts/proto`.
From a checkout of that repo:

```bash
scripts/generate.sh <module-saas-starter>/module/services/accounts/proto
```

That builds a descriptor image for the exposed protos, strips the custom options
and shared-proto dependencies (`scripts/strip_options.py`), and regenerates
`src/saas_sdk/_gen/*_pb2.py` and their `.pyi` files. **Never hand-edit `_gen/`.**

For callable-source development, fetch the PR linked from host issue #1049,
check out its exact head commit in a separate host checkout, run the command
above, and record the full 40-character SHA in `SOURCE.txt`. The generated
method gate and Connect tests must then pass against that real contract; there
are no replacement fixture protos. Before release, replace the development ref
with the accepted host tag's commit, regenerate again, and match the host module
version.

## Consuming

Import `saas_sdk`, never `saas_sdk._gen`. Each facade re-exports the message
types it takes and returns, so the generated tree stays an implementation
detail:

```python
from saas_sdk import datasource
from saas_sdk.datasource import Datasource       # the message type, re-exported

sources: list[Datasource] = datasource.new(gateway).list_sources(org)
```

Likewise `work_context` re-exports `IssuedWorkContext`, `WorkContextScope`,
`WorkContextReplayPolicy` and its enum values, and `authorization_revision`
re-exports `CheckAuthorizationRevisionRequest`. These are the generated classes
themselves, not wrappers, so `isinstance` and existing imports keep working.

Naming `saas_sdk._gen` in consumer code pins this SDK's internal layout into
yours: regenerating against a newer contract, or swapping the committed tree for
a served dependency, would become a breaking change for you rather than a change
here. `tests/test_api_boundary.py` fails if a public signature reintroduces it.
