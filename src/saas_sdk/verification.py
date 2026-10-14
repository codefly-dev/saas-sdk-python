"""Request-local Core verification through the host's accounts/authority port.

Tokens remain opaque. This client owns transport and result bounds, never token
parsing, signature verification, sealed authority, replay state or resource policy.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import timezone

from google.protobuf.message import DecodeError

from ._gen import work_contexts_pb2 as pb
from .authorization_revision import (
    RevisionUnavailable,
    _internal_credential,
    _mesh_address,
)

__all__ = [
    "VERIFY_PATH", "InvalidContext", "AuthorityDenied", "AuthorityUnavailable",
    "Scope", "VerifiedContext", "Client",
]

try:
    import grpc
except ImportError:
    grpc = None

_SERVICE = pb.DESCRIPTOR.services_by_name["WorkContextService"]
VERIFY_PATH = "/" + _SERVICE.full_name + "/" + _SERVICE.methods_by_name["VerifyIdempotent"].name


class InvalidContext(Exception):
    """The host refused the presented capability."""


class AuthorityDenied(Exception):
    """The host refused revoked authority or an unsupported replay form."""


class AuthorityUnavailable(Exception):
    """No authority decision was obtained; no identity is available."""


@dataclass(frozen=True)
class Scope:
    resource_kind: str
    actions: tuple[str, ...]
    resource_ids: tuple[str, ...]


@dataclass(frozen=True)
class VerifiedContext:
    """A host answer for one request, not a credential or Core Verified object.

    Recheck the original token at each authority checkpoint. Never persist this
    object. Its private association prevents rechecking it with another client.
    """

    tenant_id: str
    owner_principal_id: str
    current_actor_principal_id: str
    task_id: str
    expires_at_unix: int
    effective_scopes: tuple[Scope, ...]
    _token: str = field(repr=False)
    _client: object = field(repr=False)


def _bounded(value, maximum):
    return isinstance(value, str) and 0 < len(value.encode("utf-8")) <= maximum


class Client:
    """h2c on Codefly's resolved accounts/authority endpoint, protected by mesh.

    Supply independently configured issuer/audience and a fresh internal-token
    callback. The total three-second budget includes credential acquisition.
    There is no retry, fallback origin, authority cache or replay consumption.
    """

    def __init__(self, address, credential, *, issuer, audience):
        if grpc is None:
            raise ImportError("Install saas-sdk-python[revision-grpc] for verification")
        if not _bounded(issuer, 512) or not _bounded(audience, 512):
            raise ValueError("Work Context issuer and audience must be configured")
        self.issuer, self.audience, self.credential = issuer, audience, credential
        self._seal = object()
        self.channel = grpc.aio.insecure_channel(
            _mesh_address(address),
            options=(("grpc.enable_retries", 0), ("grpc.enable_http_proxy", 0),
                     ("grpc.max_receive_message_length", 65536),
                     ("grpc.max_send_message_length", 65536)),
        )
        self.rpc = self.channel.unary_unary(
            VERIFY_PATH,
            request_serializer=pb.VerifyIdempotentWorkContextRequest.SerializeToString,
            response_deserializer=pb.VerifyIdempotentWorkContextResponse.FromString,
        )

    async def verify(self, token: str) -> VerifiedContext:
        if not _bounded(token, 32768):
            raise InvalidContext("Invalid Work Context")
        try:
            return await asyncio.wait_for(self._verify(token), timeout=3.0)
        except (asyncio.TimeoutError, RevisionUnavailable, OSError, ValueError, DecodeError):
            raise AuthorityUnavailable("Work Context authority is unavailable") from None
        except grpc.aio.AioRpcError as error:
            if error.code() == grpc.StatusCode.INVALID_ARGUMENT:
                raise InvalidContext("Invalid Work Context") from None
            if error.code() in (grpc.StatusCode.PERMISSION_DENIED, grpc.StatusCode.FAILED_PRECONDITION):
                raise AuthorityDenied("Work Context authority was not confirmed") from None
            raise AuthorityUnavailable("Work Context authority is unavailable") from None

    async def _verify(self, token):
        credential = await _internal_credential(self.credential)
        response = await self.rpc(
            pb.VerifyIdempotentWorkContextRequest(
                work_context_token=token,
                expected_issuer=self.issuer,
                expected_audience=self.audience,
            ),
            metadata=(("x-codefly-internal-token", credential),),
            timeout=3.0, wait_for_ready=False,
        )
        identifiers = (response.tenant_id, response.owner_principal_id,
                       response.current_actor_principal_id, response.task_id)
        if not all(_bounded(value, 512) for value in identifiers) or not response.HasField("expires_at"):
            raise ValueError("Invalid verification response")
        response.expires_at.ToDatetime(tzinfo=timezone.utc)  # Validate timestamp range.
        if response.expires_at.nanos != 0 or response.expires_at.seconds <= 0 or len(response.effective_scopes) > 64:
            raise ValueError("Invalid verification response")
        scopes = []
        for scope in response.effective_scopes:
            if (not _bounded(scope.resource_kind, 128)
                or not 1 <= len(scope.actions) <= 64
                or not all(_bounded(value, 128) for value in scope.actions)
                or len(scope.resource_ids) > 256
                or not all(_bounded(value, 512) for value in scope.resource_ids)):
                raise ValueError("Invalid verification scope")
            scopes.append(Scope(scope.resource_kind, tuple(scope.actions), tuple(scope.resource_ids)))
        return VerifiedContext(*identifiers, response.expires_at.seconds, tuple(scopes), token, self._seal)

    async def recheck(self, verified: VerifiedContext) -> None:
        if not isinstance(verified, VerifiedContext) or verified._client is not self._seal:
            raise InvalidContext("Request-local verification evidence is required")
        current = await self.verify(verified._token)
        if current != verified:
            raise InvalidContext("Verified identity or authority changed")

    async def aclose(self) -> None:
        await self.channel.close()
