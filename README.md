# saas-sdk-python

The **Python SDK for the saas accounts API** — the Python twin of
[`saas-sdk-go`](https://github.com/codefly-dev/saas-sdk-go). A versioned,
published client that solutions depend on instead of regenerating their own
bindings.

Everything ships under a single top-level package, `saas_sdk`, so installing it
never claims a generic name (`saas`, `buf`, `datasource`) in the consumer's
import namespace.

Three layers:

- **`saas_sdk._gen`** — the generated protobuf message bindings (`*_pb2`), from
  the accounts public proto at the ref recorded in `SOURCE.txt`. Only message
  types are generated; the runtime owns the Connect transport, so there are no
  client/server stubs. The bindings embed **only** the datasource proto — the
  `buf.validate` / `saas.policy` custom options and their shared descriptors are
  stripped during generation, so this SDK never registers a shared proto into
  the global descriptor pool (which would collide with a sibling saas SDK).
  `google.protobuf.Timestamp` stays a runtime well-known type.
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
- **`saas_sdk.work_context`** — the callee half of delegated-authority checking:
  a verifier for a presented `x-codefly-work-context` header. See below.

## Work Context verification

A Work Context is a signed, delegated-authority capability carried in the
`x-codefly-work-context` header. This SDK is the **callee** half — it verifies a
presented context so a Python service can participate in delegated-authority
checks. Minting and attenuating contexts is an authority-side concern that lives
with the signer in [`sdk-go`](https://github.com/codefly-dev/sdk-go) and is not
part of this SDK.

The wire format is **not a JWT**. A token is
`base64url(JSON payload).base64url(Ed25519 sig)`, the payload is a fixed
snake_case JSON object, and `key_id` lives *inside* the payload. Field order,
`uint64`-as-decimal-string encoding, scope canonicalization, base64url, and
Ed25519 signing are pinned byte-for-byte to `sdk-go`: the wire golden in
`tests/fixtures/work_context_wire_golden.json` is byte-identical to sdk-go's
`TestWorkContextWireGolden`, and CI in both repos verifies the same token.

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
failure. Replay policy is reported on the claims; enforcing single-use
consumption still requires a durable replay store the caller owns.

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

That builds a descriptor image for `datasource.proto`, strips the custom options
and shared-proto dependencies (`scripts/strip_options.py`), and regenerates
`src/saas_sdk/_gen/datasource_pb2.py`. **Never hand-edit `_gen/`.**

## Consuming

```python
from saas_sdk import datasource                 # the facade
from saas_sdk._gen import datasource_pb2         # the message types
```
