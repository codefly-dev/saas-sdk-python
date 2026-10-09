# Changelog

## Unreleased

- Prepare `datasource.invoke`, `lookup`, `declare_operations` and
  `list_operations`, also available on the existing gateway-bound client.
- Add operation declarations, effects, results, receipts, UUIDv7 effect IDs,
  and typed host errors matching the Go SDK's callable-source surface.
- Preserve gateway authority and host error messages; delegate replay to the
  host and return unknown lookup outcomes as values.
- Document call options, receipt recovery and the host's disclosure boundary
  in `README.md`, with an executable `example.com` provider example.
- Development is blocked on the callable-source proto in
  `codefly-dev/module-saas-starter#1049` and runtime gateway support for Work
  Context, per-call headers and timeouts. No bindings or release version have
  been changed; release requires the host tag and successful regeneration.
