---
name: regenerate-bindings
description: Regenerate src/saas_sdk/_gen from the accounts proto in module-saas-starter — running scripts/generate.sh, the option-stripping step that keeps shared descriptors out of the global pool, and the SOURCE.txt record. Use when the accounts proto changed, when a new message or proto file has to be exposed, or when a review asks why _gen looks different from a plain buf generate.
---

# Regenerating the protobuf bindings

`src/saas_sdk/_gen` is generated, never hand-edited. An edit there is silently
reverted by the next regeneration and is not a fix.

## Source of truth

The protos live in `module-saas-starter` at
`module/services/accounts/proto`. Two files are exposed by this SDK:
`saas/accounts/v1/datasource.proto` and `saas/accounts/v1/work_contexts.proto`
(the list is `protos=()` in `scripts/generate.sh`).

The commit those bindings came from is recorded in `SOURCE.txt`. Read it before
regenerating: if the proto change you need is not yet merged in
`module-saas-starter`, that merge is the first pull request, not a local
checkout regenerated against an unmerged branch.

## The walk

From a checkout of `module-saas-starter`:

```bash
scripts/generate.sh <module-saas-starter>/module/services/accounts/proto
```

Requires `buf` and a `python3` with the `protobuf` package importable (the
script calls `scripts/strip_options.py` with plain `python3`, not the project
venv — activate the venv if the system interpreter lacks `protobuf`).

Then, in the same pull request:

1. Update `SOURCE.txt` — the `module-saas-starter` commit SHA, and the module
   version if it moved. That version is also this SDK's release version in
   `pyproject.toml`; the two are matched on purpose.
2. Run the suite: `python -m pytest -q`.
3. If a new proto file is exposed, add it to `protos=()` in
   `scripts/generate.sh`, to the service list in `SOURCE.txt`, and to the
   package description in `README.md`.

## Why generation is not plain `buf generate`

The script builds a descriptor image, then `scripts/strip_options.py` removes
the custom options (`buf.validate`, `saas.policy`) and the `google.api` HTTP
annotations together with their shared-proto dependencies, and only then
generates. Without that step the bindings embed shared descriptors and register
them into the **global descriptor pool**, where they collide at import time with
any sibling saas SDK that did the same. The well-known `google.protobuf` types
are deliberately left as runtime types.

Message bindings only: `buf.gen.yaml` generates no client or server stubs,
because the solution runtime owns the Connect transport and this SDK calls
through `Gateway.unary`. Do not add a grpc plugin to get a stub — if a consumer
needs a call this SDK does not expose, the facade
(`src/saas_sdk/datasource.py`) grows a method that names the procedure.

## Version floors

`buf.gen.yaml` pins both plugins to `v29.3`, which is the gencode line matching
the `protobuf>=5.29.3` floor in `pyproject.toml`. Bumping the plugin without the
floor produces bindings that fail to import for consumers on protobuf 5.x;
bumping the floor without the plugin is an unmotivated break of the same
consumers. They move in one change or not at all.
