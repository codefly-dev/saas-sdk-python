"""Strip custom options + shared-proto deps from a buf image so the generated
message bindings embed only the named accounts proto(s) themselves (plus the
well-known types they reference, which come from the protobuf runtime). Removes
the buf.validate, saas.policy, and google.api imports that would otherwise force
this SDK to vendor shared descriptors into the global pool.

Usage: strip_options.py <in.binpb> <out.binpb> <proto>...

Each <proto> is a file kept in the output with its options and shared-proto
dependencies stripped; the google.protobuf well-known types those files still
reference are carried through as-is.
"""

import sys

from google.protobuf import descriptor_pb2

DROP_DEP_PREFIXES = ("buf/validate/", "saas/policy/", "google/api/")


def clear_message(message):
    message.ClearField("options")
    for field in message.field:
        field.ClearField("options")
    for nested in message.nested_type:
        clear_message(nested)
    for enum in message.enum_type:
        enum.ClearField("options")


def strip(file_proto):
    deps = [d for d in file_proto.dependency if not d.startswith(DROP_DEP_PREFIXES)]
    del file_proto.dependency[:]
    file_proto.dependency.extend(deps)
    del file_proto.public_dependency[:]
    del file_proto.weak_dependency[:]
    for message in file_proto.message_type:
        clear_message(message)
    for enum in file_proto.enum_type:
        enum.ClearField("options")
    for service in file_proto.service:
        service.ClearField("options")
        for method in service.method:
            method.ClearField("options")


targets = set(sys.argv[3:])

source = descriptor_pb2.FileDescriptorSet()
source.ParseFromString(open(sys.argv[1], "rb").read())

stripped = {}
needed_wkt = set()
for file_proto in source.file:
    if file_proto.name in targets:
        strip(file_proto)
        needed_wkt.update(
            d for d in file_proto.dependency if d.startswith("google/protobuf/")
        )
        stripped[file_proto.name] = file_proto

# Source order is topological (a file's dependencies precede it), so keeping it
# leaves every referenced well-known type ahead of the file that needs it.
out = descriptor_pb2.FileDescriptorSet()
for file_proto in source.file:
    if file_proto.name in stripped:
        out.file.append(stripped[file_proto.name])
    elif file_proto.name in needed_wkt:
        out.file.append(file_proto)

open(sys.argv[2], "wb").write(out.SerializeToString())
print("kept:", [f.name for f in out.file], file=sys.stderr)
