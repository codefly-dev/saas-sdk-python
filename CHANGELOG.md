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
  `2a16c688c61d66645e1063c495fa38eaf2fa52de`. Calls carry JSON objects in
  `input_json`/`output_json` strings; lookup selects only the effect ID, and
  receipts decode the host's text status and RFC3339 commit time.
- Include the host's `PruneSourceOperationReceipts` and its lookup in generated
  bindings only; runtime-scheduled retention has no caller facade.
- Strip Runnable annotations in the generation pipeline alongside other
  custom options, keeping shared descriptors out of the SDK's generated tree.
- The source ref is a development PR head; release still requires the host
  tag. Runtime gateway support for Work Context, per-call headers and timeouts
  remains a prerequisite for production calls. The release version is unchanged.
- Distinguish unknown mutation outcomes, provider refusals, effect reuse and
  other precondition reasons. Preserve effect IDs on every dispatched failure,
  including non-Connect HTTP errors, and keep raw error bodies readable.
- Return `EffectNotFound` from lookup with `NOT_ATTEMPTED`; document same-ID
  recovery when no attempt marker exists. The host preserves receipt lookup
  across declaration removal or replacement under current source authority. Add
  committed `Receipt.output` and operation `description`/read-only `digest`,
  matching Go #30; remove the unused `REFUSED` receipt status.
- Add `OperationDeclarationRemoved` for the host's
  `SOURCE_OPERATION_DECLARATION_REMOVED` reason, matching Go. Preserve the effect
  ID and `receipt_status` (`COMMITTED` or conservatively `UNKNOWN`) on its receipt.
  Recovery uses lookup with the original ID, never a fresh-ID retry. Lookup
  returns this typed outcome if the host sends it there.
- Validate UTF-8 effect IDs against the host byte limit, report declaration
  parsing failures as typed errors, and diagnose unsupported runtime gateways
  before dispatch. Document the timeout and host error-detail limitations and
  the exact scope and stub packages used for strict mypy.
- Unify non-Connect HTTP 4xx/5xx (including 429 and 500) as `OutcomeUnknown`
  after dispatch, while preserving recognized Connect errors. Expired or
  non-finite deadlines raise `InputError` before any host call.
- Consume the new host's explicit `provider_status` metadata for
  `SOURCE_PROVIDER_REFUSED`, accepting only three ASCII digits in 100–599.
  Missing or invalid metadata stays absent; never infer status from prose or
  the outer HTTP response. Test the host's concrete 403 refusal and `/id`
  `BadRequest.FieldViolation` shape, including its `SOURCE_INPUT_REFUSED` detail.
- Return `OutcomeUnknown` with the original receipt/ID from lookup on transport
  loss, an undecodable protobuf response or invalid receipt identity/status/time.
- Preserve valid COMMITTED evidence in `DatasourceError` when either output JSON
  field is invalid. `Receipt.output` uses `receipt.output_json`; `Result.output`
  uses top-level `output_json`. Both fields validate on committed invoke/lookup.
- Match management error mappings: non-Connect HTTP 403 on declare/list becomes
  `NotPermitted`; their host unknown-outcome reason remains `OperationRefused`.
  Pin accepted UTF-8 charset/BOM and case-insensitive gzip error envelopes.
- Require explicit schema objects before declaring operations: omitted schemas
  default to `None` and raise `InputError` without dispatch. Explicit `{}` remains
  accepted; absent schemas in list responses become `{}`.
- Document the host timestamp profile and Python's existing protobuf parser
  limits, without changing timestamp parsing.
- Reject unsupported response encodings before inferring host status:
  declare/list raises `DatasourceError`; invoke/lookup retains `OutcomeUnknown`
  and the original effect receipt. Keep the original error body readable.
- Report an unspecified effect in a listed operation as `InputError`, including
  omitted/default effects, matching the Go SDK.
