"""The generated bindings load together and resolve every cross-file reference.

datasource.proto reads its sync state from saas.jobs.v1, which the generator
renames into this package (saas_sdk/_gen/jobs.proto) so the generated import
resolves here instead of naming a top-level `saas` package this SDK does not
own. A binding that imported an unresolvable module, or referenced a type the
pool never loaded, fails at import time; these tests pin both.
"""

from saas_sdk._gen import datasource_pb2, jobs_pb2, work_contexts_pb2


def test_sync_state_resolves_to_the_jobs_enum():
    field = datasource_pb2.GetSourceSyncResponse.DESCRIPTOR.fields_by_name["state"]
    assert field.enum_type.full_name == "saas.jobs.v1.JobState"
    assert field.enum_type.file.name == "saas_sdk/_gen/jobs.proto"


def test_sync_state_round_trips_through_the_wire():
    state = jobs_pb2.JobState.Value(jobs_pb2.JobState.Name(1))
    response = datasource_pb2.GetSourceSyncResponse(state=state)
    decoded = datasource_pb2.GetSourceSyncResponse.FromString(response.SerializeToString())
    assert decoded.state == state


def test_the_generated_files_register_no_shared_option_protos():
    for module in (datasource_pb2, jobs_pb2, work_contexts_pb2):
        deps = [d.name for d in module.DESCRIPTOR.dependencies]
        assert not any(d.startswith(("buf/validate/", "saas/policy/", "google/api/")) for d in deps), deps
