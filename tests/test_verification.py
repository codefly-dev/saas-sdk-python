import asyncio
from dataclasses import replace

import grpc
import pytest
import pytest_asyncio

from saas_sdk import verification as v
from saas_sdk._gen import work_contexts_pb2 as pb


@pytest_asyncio.fixture
async def authority():
    state = {"calls": [], "code": None, "response": pb.VerifyIdempotentWorkContextResponse(
        tenant_id="tenant", owner_principal_id="owner", current_actor_principal_id="actor",
        task_id="task", expires_at={"seconds": 2000000000},
        effective_scopes=[{"resource_kind": "records", "actions": ["read"], "resource_ids": ["one"]}],
    )}

    async def verify(request, context):
        state["calls"].append((request, dict(context.invocation_metadata())))
        if state["code"]:
            await context.abort(state["code"], "private provider failure must not escape")
        return state["response"]

    server = grpc.aio.server()
    server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler(
        "saas.accounts.v1.WorkContextService", {"VerifyIdempotent": grpc.unary_unary_rpc_method_handler(
            verify,
            request_deserializer=pb.VerifyIdempotentWorkContextRequest.FromString,
            response_serializer=pb.VerifyIdempotentWorkContextResponse.SerializeToString,
        )}),))
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    refreshes = []

    async def credential():
        refreshes.append(len(refreshes) + 1)
        return f"perimeter-{len(refreshes)}"

    client = v.Client(f"127.0.0.1:{port}", credential, issuer="trusted-issuer", audience="consumer")
    try:
        yield client, state, refreshes
    finally:
        await client.aclose()
        await server.stop(0)


@pytest.mark.asyncio
async def test_opaque_token_trusted_expectations_and_fresh_recheck(authority):
    client, state, refreshes = authority
    token = "opaque-presented-capability"
    verified = await client.verify(token)
    assert verified.tenant_id == "tenant"
    assert verified.effective_scopes == (v.Scope("records", ("read",), ("one",)),)
    assert token not in repr(verified)
    await client.recheck(verified)
    assert refreshes == [1, 2]
    for i, (request, metadata) in enumerate(state["calls"], 1):
        assert request.work_context_token == token
        assert request.expected_issuer == "trusted-issuer"
        assert request.expected_audience == "consumer"
        assert metadata["x-codefly-internal-token"] == f"perimeter-{i}"
    with pytest.raises(v.InvalidContext):
        await client.recheck(replace(verified, _client=object()))
    state["response"].owner_principal_id = "different-owner"
    with pytest.raises(v.InvalidContext):
        await client.recheck(verified)


@pytest.mark.asyncio
@pytest.mark.parametrize("code,exception", [
    (grpc.StatusCode.INVALID_ARGUMENT, v.InvalidContext),
    (grpc.StatusCode.FAILED_PRECONDITION, v.AuthorityDenied),
    (grpc.StatusCode.PERMISSION_DENIED, v.AuthorityDenied),
    (grpc.StatusCode.UNAUTHENTICATED, v.AuthorityUnavailable),
    (grpc.StatusCode.UNAVAILABLE, v.AuthorityUnavailable),
    (grpc.StatusCode.DEADLINE_EXCEEDED, v.AuthorityUnavailable),
])
async def test_failures_never_return_identity_or_disclose_details(authority, code, exception):
    client, state, _ = authority
    state["code"] = code
    with pytest.raises(exception) as caught:
        await client.verify("opaque")
    assert "private" not in str(caught.value)


@pytest.mark.asyncio
async def test_empty_or_changed_response_fails_closed(authority):
    client, state, _ = authority
    state["response"].ClearField("tenant_id")
    with pytest.raises(v.AuthorityUnavailable):
        await client.verify("opaque")


@pytest.mark.asyncio
async def test_credential_failure_and_deadline_do_not_call_host(authority):
    client, state, _ = authority

    async def failure():
        raise RuntimeError("sensitive detail")

    client.credential = failure
    with pytest.raises(v.AuthorityUnavailable):
        await client.verify("opaque")

    async def slow():
        await asyncio.sleep(30)
        return "never"

    client.credential = slow
    with pytest.raises(v.AuthorityUnavailable):
        await asyncio.wait_for(client.verify("opaque"), timeout=4)
    assert not state["calls"]


@pytest.mark.asyncio
async def test_oversize_token_is_refused_before_transport(authority):
    client, state, _ = authority
    with pytest.raises(v.InvalidContext):
        await client.verify("x" * 32769)
    assert not state["calls"]
