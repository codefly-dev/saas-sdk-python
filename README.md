# saas-sdk-python

The **Python SDK for the saas accounts API** — the Python twin of
[`saas-sdk-go`](https://github.com/codefly-dev/saas-sdk-go). A versioned,
published client that solutions depend on instead of regenerating their own
bindings.

Everything ships under a single top-level package, `saas_sdk`, so installing it
never claims a generic name (`saas`, `buf`, `datasource`) in the consumer's
import namespace.

Two layers:

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

- **`saas_sdk.work_context`** — callee-side verification of a signed **Work
  Context**, the capability accounts mints when a user delegates a Task to an
  agent (the twin of `sdk-go`'s `work_context.go`). See below.

## Work Context verification

A Work Context arrives in the `x-codefly-work-context` header (HTTP and gRPC
metadata alike). It is **not** a JWT: two base64url segments,
`payload.signature`, where the payload is one fixed snake_case JSON layout
(`codefly.work-context/v1`) and the signature is Ed25519 over the raw payload
bytes. The verifier mirrors sdk-go v0.1.65 check for check — canonical
encoding, signature by `key_id`, strict decoding, structural bounds, time window
(60s skew, 15-minute cap), then the callee's expectations — and the Go-minted
golden fixture under `tests/fixtures/` pins the interop.

Keys come from the accounts JWKS at `GET /v1/auth/.well-known/jwks.json`
(`kty=OKP`, `crv=Ed25519`; the Work Context signing key **is** the access-token
key, same `kid`). `JWKSKeySource` mirrors sdk-go's `WorkContextJWKSVerifier`:
a 5-minute cache, one refresh per cache generation on an unknown `kid` (rotation
is picked up at once, guessed kids can't cause a fetch storm), and it never
fails open — no keys, a non-JWKS body, or a fetch error is a verification
error. `from_url` is the Go constructor shape (redirects refused, 256 KiB and
`application/json` bounds, 2s timeout); the fetcher is also injectable, so any
HTTP client works.

```python
from saas_sdk import jwks, work_context as wc

source = jwks.JWKSKeySource.from_url(f"{ACCOUNTS_URL}/v1/auth/.well-known/jwks.json")
ctx = source.verify(
    wc.from_headers(request.headers),   # HTTP headers or gRPC metadata pairs; a duplicated carrier is rejected
    wc.WorkContextExpectations(issuer="saas-starter", audience="my-service"),
)
ctx.owner_principal_id, ctx.current_actor, ctx.effective_scopes, ctx.authorization_revision
ctx.require_scope("robin:tasks", "execute")      # WorkContextDenied if not granted
ctx.has_scope("repository", "write", "repo-1")   # empty resource_ids = every resource of the kind
```

`WorkContextError` means the token is untrusted (fail closed → 401);
`WorkContextDenied` means a trusted context lacks the scope (403). Scopes are
evaluated against the **current actor** — the last hop of `actor_chain`, or the
owner's `authority_scopes` on a direct call.

With FastAPI (`pip install saas-sdk-python[fastapi]`), one dependency does the
header read, verification, and scope gate — the twin of `verify_obo_token` +
`require_permission` in the callees being ported:

```python
from fastapi import Depends, FastAPI
from saas_sdk.work_context_fastapi import WorkContextAuth

auth = WorkContextAuth(source, audience="my-service")   # issuer defaults to "saas-starter"
app = FastAPI()

@app.post("/tasks/{task_id}/run")
def run(task_id: str, ctx: wc.WorkContext = Depends(auth.require_scope("robin:tasks", "execute"))):
    ...

@app.post("/repos/{repo}/write")
def write(repo: str, ctx=Depends(auth.require_scope("repository", "write", lambda r: r.path_params["repo"]))):
    ...
```

Status split, the same as the Go middleware: **401** for no carrier, a
duplicated carrier, or a token that doesn't verify (the verifier is asked to
match `issuer` only); **403** for a trusted context that is for a different
`audience` or whose current actor lacks the scope.

Tokens are never minted here — a callee only verifies. The Go golden fixture is
regenerated with sdk-go's `WorkContextSigner` (`tests/fixtures/`); don't
hand-edit it.

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
