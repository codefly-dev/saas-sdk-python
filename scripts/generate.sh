#!/usr/bin/env bash
# Regenerate src/saas_sdk/_gen from the accounts proto.
#
# Usage: scripts/generate.sh <module-saas-starter>/module/services/accounts/proto
#
# The bindings deliberately embed only the datasource proto: the custom options
# (buf.validate, saas.policy) and their shared descriptors are stripped, so this
# SDK never registers a shared proto into the global descriptor pool (which would
# collide with a sibling saas SDK). google.protobuf.Timestamp stays a runtime
# well-known type. See scripts/strip_options.py.
set -euo pipefail
proto_dir="$(cd "$1" && pwd)"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# buf resolves --path relative to the working directory, so build from inside
# the proto module.
(cd "$proto_dir" && buf build . --path saas/accounts/v1/datasource.proto -o "$tmp/image.binpb")
python3 "$repo_root/scripts/strip_options.py" "$tmp/image.binpb" "$tmp/stripped.binpb"
buf generate --template "$repo_root/buf.gen.yaml" "$tmp/stripped.binpb" -o "$tmp/out"

cp "$tmp/out/saas/accounts/v1/datasource_pb2.py"  "$repo_root/src/saas_sdk/_gen/datasource_pb2.py"
cp "$tmp/out/saas/accounts/v1/datasource_pb2.pyi" "$repo_root/src/saas_sdk/_gen/datasource_pb2.pyi"
echo "regenerated src/saas_sdk/_gen/datasource_pb2.py"
