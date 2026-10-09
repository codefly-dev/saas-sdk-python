# Changelog

## Unreleased

- Add `datasource.invoke`, `lookup`, `declare_operations` and
  `list_operations`, also available on the existing gateway-bound client.
- Add operation declarations, effects, results, receipts, UUIDv7 effect IDs,
  and typed host errors matching the Go SDK's callable-source surface.
- Preserve gateway authority and host error messages; delegate replay to the
  host and return unknown lookup outcomes as values.
- Document call options, receipt recovery and the host's disclosure boundary
  in `README.md`, with an executable `example.com` provider example.
- Regenerate from host PR #1052 head
  `f4ce896d954101b164c3b511cbeea555f17302f7`. Calls carry JSON objects in
  `input_json`/`output_json` strings; lookup selects only the effect ID, and
  receipts decode the host's text status and RFC3339 commit time.
- Strip Runnable annotations in the generation pipeline alongside other
  custom options, keeping shared descriptors out of the SDK's generated tree.
- The source ref is a development PR head; release still requires the host
  tag. Runtime gateway support for Work Context, per-call headers and timeouts
  remains a prerequisite for production calls. The release version is unchanged.
- Distinguish unknown mutation outcomes, provider refusals, effect reuse and
  other precondition reasons. Preserve effect IDs on every dispatched failure,
  including non-Connect HTTP errors, and keep raw error bodies readable.
- Return `EffectNotFound` from lookup with `NOT_ATTEMPTED`; document same-ID
  recovery and the pinned host's ambiguous lookup NotFound response. Add
  committed `Receipt.output` and operation `description`/read-only `digest`,
  matching Go #30; remove the unused `REFUSED` receipt status.
- Validate UTF-8 effect IDs against the host byte limit, report declaration
  parsing failures as typed errors, and diagnose unsupported runtime gateways
  before dispatch. Document the timeout and host error-detail limitations and
  the exact scope and stub packages used for strict mypy.
- Unify non-Connect HTTP 4xx/5xx (including 429 and 500) as `OutcomeUnknown`
  after dispatch, while preserving recognized Connect errors. Expired or
  non-finite deadlines raise `InputError` before any host call. Pin that
  `provider_status` error metadata never populates `ProviderRefused.status`.
