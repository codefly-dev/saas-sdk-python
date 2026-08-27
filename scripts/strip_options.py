"""Strip custom options + shared-proto deps from a buf image so the generated
message bindings embed only the datasource proto itself (plus the well-known
Timestamp, which comes from the protobuf runtime). Removes the buf.validate and
saas.policy imports that would otherwise force this SDK to vendor shared
descriptors into the global pool. Usage: strip_options.py <in.binpb> <out.binpb>
"""

import sys

from google.protobuf import descriptor_pb2

KEEP = {"saas/accounts/v1/datasource.proto", "google/protobuf/timestamp.proto"}
DROP_DEPS = {"buf/validate/validate.proto", "saas/policy/v1/options.proto"}


def clear_message(message):
    message.ClearField("options")
    for field in message.field:
        field.ClearField("options")
    for nested in message.nested_type:
        clear_message(nested)
    for enum in message.enum_type:
        enum.ClearField("options")


def strip(file_proto):
    deps = [d for d in file_proto.dependency if d not in DROP_DEPS]
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


source = descriptor_pb2.FileDescriptorSet()
source.ParseFromString(open(sys.argv[1], "rb").read())

out = descriptor_pb2.FileDescriptorSet()
for file_proto in source.file:
    if file_proto.name not in KEEP:
        continue
    if file_proto.name == "saas/accounts/v1/datasource.proto":
        strip(file_proto)
    out.file.append(file_proto)

open(sys.argv[2], "wb").write(out.SerializeToString())
print("kept:", [f.name for f in out.file], file=sys.stderr)
