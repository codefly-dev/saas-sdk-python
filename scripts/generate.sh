#!/usr/bin/env bash
# Regenerate src/saas_sdk/_gen from the accounts proto.
#
# Usage: scripts/generate.sh <module-saas-starter>/module/services/accounts/proto
#
# The bindings deliberately embed only the accounts protos this SDK exposes: the
# custom options (buf.validate, saas.policy) and their shared descriptors, plus
# the google.api HTTP annotations, are stripped, so this SDK never registers a
# shared proto into the global descriptor pool (which would collide with a
# sibling saas SDK). The google.protobuf well-known types stay runtime types.
# See scripts/strip_options.py.
set -euo pipefail
proto_dir="$(cd "$1" && pwd)"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

protos=(
  saas/accounts/v1/datasource.proto
  saas/accounts/v1/work_contexts.proto
)

# buf resolves --path relative to the working directory, so build from inside
# the proto module.
paths=()
for proto in "${protos[@]}"; do paths+=(--path "$proto"); done
(cd "$proto_dir" && buf build . "${paths[@]}" -o "$tmp/image.binpb")
python3 "$repo_root/scripts/strip_options.py" "$tmp/image.binpb" "$tmp/stripped.binpb" "${protos[@]}"
buf generate --template "$repo_root/buf.gen.yaml" "$tmp/stripped.binpb" -o "$tmp/out"

for proto in "${protos[@]}"; do
  base="$(basename "$proto" .proto)"
  cp "$tmp/out/saas/accounts/v1/${base}_pb2.py"  "$repo_root/src/saas_sdk/_gen/${base}_pb2.py"
  cp "$tmp/out/saas/accounts/v1/${base}_pb2.pyi" "$repo_root/src/saas_sdk/_gen/${base}_pb2.pyi"
done
echo "regenerated src/saas_sdk/_gen from ${#protos[@]} proto(s)"
