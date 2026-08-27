# saas-sdk-python

The **Python SDK for the saas accounts API** — the Python twin of
[`saas-sdk-go`](https://github.com/codefly-dev/saas-sdk-go). A versioned,
published client that solutions depend on instead of regenerating their own
bindings.

Two layers:

- **`gen/`** — the generated protobuf message bindings (`*_pb2.py` / `*.pyi`) for
  the accounts public proto, generated from `codefly-dev/module-saas-starter` at
  the ref recorded in `SOURCE.txt`. Only message types are generated; the
  runtime owns the Connect transport, so there are no client/server stubs.
- **`datasource/`** — a gateway-bound facade over those types. It names the
  Connect procedure and routes the call through the solution runtime's
  `Gateway.unary(procedure, request, response_type)` seam, so a solution
  connects a GitHub datasource collection in a few lines:

  ```python
  from datasource import new

  ds = new(gateway)
  source = ds.add_github_source(
      org_id=org,
      repo="codefly-dev/module-saas-starter",
      paths=["docs"],
      collection="handbook",
      access_token=token,
  )
  ds.sync_source(org, source.id)
  ```

  `gateway` is any value exposing `unary(procedure, request, response_type)` —
  which `solution_runtime.Gateway` already satisfies. The runtime stays
  datasource-agnostic and takes **no** dependency on this SDK.

## Versioning

This SDK's release version tracks the **saas-starter module version**
(`module/module.package.codefly.yaml`), recorded in `SOURCE.txt` alongside the
proto ref `gen/` was generated from.

## Regenerating `gen/`

The proto source of truth is `module-saas-starter/module/services/accounts/proto`.
To refresh (from a checkout of that repo):

```bash
cd module/services/accounts/proto
buf generate --template <this-repo>/buf.gen.yaml -o <this-repo> \
    --path saas/accounts/v1/datasource.proto
```

`buf.gen.yaml` sets `include_imports: true`, so the proto's non-well-known
imports (`buf.validate`, `saas.policy.v1`) are emitted into the tree while
`google.protobuf.*` well-knowns come from the `protobuf` runtime. **Never
hand-edit `gen/`** — the descriptors embed length-prefixed package strings that
a text rewrite corrupts. Always regenerate.

## Consuming

```python
from datasource import new                     # the facade
from saas.accounts.v1 import datasource_pb2     # the message types
```

Add both source roots to the import path (the repo installs them as top-level
`datasource`, `saas`, and `buf` packages via `pip install`).
