"""Accounts current-revision protocol for already verified Work Context claims.

The caller retains signature, lifetime, scope and resource policy. Every check
refreshes its internal credential and contacts the authority; no decision is cached.
Networking dependencies are optional extras so projection remains lightweight.
"""

import asyncio
import json
import ssl
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from google.protobuf.json_format import MessageToDict

from ._gen import work_contexts_pb2 as pb
from .work_context import WorkContext

try:
    import grpc
except ImportError:
    grpc = None
try:
    import httpx
except ImportError:
    httpx = None

_SERVICE = pb.DESCRIPTOR.services_by_name["WorkContextService"]
_METHOD = _SERVICE.methods_by_name["CheckAuthorizationRevision"]
REVISION_PATH = "/" + _SERVICE.full_name + "/" + _METHOD.name
TIMEOUT = 3.0


class RevisionDenied(Exception):
    """Accounts reported PermissionDenied or a stale/revoked revision."""


class RevisionUnavailable(Exception):
    """Internal credential, transport or response-contract failure; no authority granted."""


def _decode(data):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("Duplicate JSON key")
            value[key] = item
        return value

    def invalid(value):
        raise ValueError("Non-finite JSON value")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


async def _internal_credential(provider: Callable[[], Awaitable[str]]) -> str:
    try:
        token = await provider()
    except Exception:
        raise RevisionUnavailable("Current authority is unavailable") from None
    if (
        not isinstance(token, str)
        or not 1 <= len(token) <= 8192
        or any(ord(c) < 33 or ord(c) > 126 for c in token)
    ):
        raise RevisionUnavailable("Current authority is unavailable")
    return token


def _https_origin(value: str) -> str:
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.path not in ("", "/")
        or url.query
        or url.fragment
        or "\\" in value
        or any(c.isspace() or ord(c) < 32 for c in value)
        or url.port == 0
    ):
        raise ValueError("Accounts requires an explicit HTTPS internal origin")
    return value.rstrip("/")


def revision_request(claims: WorkContext) -> pb.CheckAuthorizationRevisionRequest:
    """Copy owner and every actor scope; the caller owns verification and policy."""
    if (
        not isinstance(claims, WorkContext)
        or not claims.tenant_id
        or not claims.owner_principal_id
    ):
        raise RevisionUnavailable("Current authority is unavailable")

    def subject(principal, scopes):
        if not principal:
            raise RevisionUnavailable("Current authority is unavailable")
        return pb.WorkContextRevisionSubject(
            principal_id=principal,
            scopes=[
                pb.WorkContextScope(
                    resource_kind=s.resource_kind,
                    actions=s.actions,
                    resource_ids=s.resource_ids,
                )
                for s in scopes
            ],
        )

    return pb.CheckAuthorizationRevisionRequest(
        org_id=claims.tenant_id,
        owner_principal_id=claims.owner_principal_id,
        authorization_revision=claims.authorization_revision,
        subjects=[
            subject(claims.owner_principal_id, claims.authority_scopes),
            *(subject(a.principal_id, a.granted_scopes) for a in claims.actor_chain),
        ],
    )


class ConnectClient:
    """Connect compatibility client; select only when the authority endpoint serves Connect."""

    def __init__(self, origin, credential, *, transport=None, tls_context=None):
        if httpx is None:
            raise ImportError(
                "Install saas-sdk-python[revision-connect] for Connect revision checks"
            )
        self.endpoint = _https_origin(origin) + REVISION_PATH
        self.credential = credential
        if tls_context is not None and (
            not tls_context.check_hostname
            or tls_context.verify_mode != ssl.CERT_REQUIRED
        ):
            raise ValueError("Accounts TLS verification cannot be disabled")
        self.client = httpx.AsyncClient(
            transport=transport
            if transport is not None
            else httpx.AsyncHTTPTransport(
                retries=0, trust_env=False, verify=tls_context if tls_context else True
            ),
            trust_env=False,
            follow_redirects=False,
        )

    async def check(self, claims: WorkContext) -> None:
        try:
            await asyncio.wait_for(self._check(claims), timeout=TIMEOUT)
        except asyncio.TimeoutError:
            raise RevisionUnavailable("Current authority is unavailable") from None

    async def _check(self, claims):
        response = None
        try:
            # Includes credential refresh, pool wait, connection and the complete body.
            token = await _internal_credential(self.credential)
            body = MessageToDict(
                revision_request(claims), preserving_proto_field_name=True
            )
            # Construct directly: never inherit caller headers, client cookies or auth.
            request = httpx.Request(
                "POST",
                self.endpoint,
                headers={
                    "content-type": "application/json",
                    "accept": "application/json",
                    "accept-encoding": "identity",
                    "connect-protocol-version": "1",
                    "x-codefly-internal-token": token,
                },
                content=json.dumps(body).encode(),
                extensions={
                    "timeout": dict.fromkeys(("connect", "read", "write", "pool"), 3)
                },
            )
            response = await self.client.send(request, stream=True, auth=None)
            if response.status_code not in (200, 400, 403):
                raise ValueError("Accounts unavailable")
            if (
                response.headers.get("content-type", "").split(";", 1)[0]
                != "application/json"
            ):
                raise ValueError("Invalid Accounts response type")
            if response.headers.get("content-encoding", "identity") != "identity":
                raise ValueError("Compressed Accounts responses are not supported")
            data = bytearray()
            async for part in response.aiter_bytes():
                data.extend(part)
                if len(data) > 8192:
                    raise ValueError("Accounts response exceeds bound")
            payload = _decode(data)
            if response.status_code != 200:
                # Connect maps gRPC FailedPrecondition to 400, not HTTP 412.
                # An internal 401 is a service credential outage, never caller denial.
                if isinstance(payload, dict) and (
                    response.status_code,
                    payload.get("code"),
                ) in (
                    (400, "failed_precondition"),
                    (403, "permission_denied"),
                ):
                    raise RevisionDenied("Current authority was not confirmed")
                raise ValueError("Invalid Accounts error response")
            if payload != {}:
                raise ValueError("Expected canonical empty revision response")
        except (httpx.HTTPError, OSError, ValueError, TimeoutError):
            raise RevisionUnavailable("Current authority is unavailable") from None
        finally:
            if response is not None:
                await response.aclose()

    async def aclose(self) -> None:
        await self.client.aclose()


class GRPCClient:
    """TLS gRPC on the canonical internal RPC; no retries, fallback or authority cache."""

    def __init__(self, origin, credential, *, tls_context=None):
        if grpc is None:
            raise ImportError(
                "Install saas-sdk-python[revision-grpc] for gRPC revision checks"
            )
        url = urlsplit(_https_origin(origin))
        self.credential = credential
        context = (
            tls_context if tls_context is not None else ssl.create_default_context()
        )
        if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
            raise ValueError("Accounts TLS verification cannot be disabled")
        # Use the deployment-selected trust roots, not gRPC environment overrides.
        roots = b"".join(
            ssl.DER_cert_to_PEM_cert(cert).encode("ascii")
            for cert in context.get_ca_certs(binary_form=True)
        )
        if not roots:
            raise ValueError("Accounts requires trusted TLS roots")
        host = f"[{url.hostname}]" if ":" in url.hostname else url.hostname
        self.channel = grpc.aio.secure_channel(
            f"{host}:{url.port or 443}",
            grpc.ssl_channel_credentials(root_certificates=roots),
            options=(
                ("grpc.enable_retries", 0),
                ("grpc.enable_http_proxy", 0),
                ("grpc.max_receive_message_length", 8192),
                ("grpc.max_send_message_length", 65536),
            ),
        )
        self.rpc = self.channel.unary_unary(
            REVISION_PATH,
            request_serializer=pb.CheckAuthorizationRevisionRequest.SerializeToString,
            # The canonical response is google.protobuf.Empty. Reject unknown fields
            # rather than silently accepting a different response contract.
            response_deserializer=lambda data: data,
        )

    async def check(self, claims: WorkContext) -> None:
        try:
            await asyncio.wait_for(self._check(claims), timeout=TIMEOUT)
        except asyncio.TimeoutError:
            raise RevisionUnavailable("Current authority is unavailable") from None

    async def _check(self, claims):
        try:
            # One total budget includes credential refresh, connection and RPC body.
            deadline = asyncio.get_running_loop().time() + TIMEOUT
            token = await _internal_credential(self.credential)
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError
            response = await self.rpc(
                revision_request(claims),
                metadata=(("x-codefly-internal-token", token),),
                timeout=remaining,
                wait_for_ready=False,
            )
            if response != b"":
                raise ValueError("Expected canonical empty revision response")
        except grpc.aio.AioRpcError as error:
            if error.code() in (
                grpc.StatusCode.PERMISSION_DENIED,
                grpc.StatusCode.FAILED_PRECONDITION,
            ):
                raise RevisionDenied("Current authority was not confirmed") from None
            # Internal credential failures are service outages, never caller denials.
            # Do not expose provider details, trailers, metadata or credentials.
            raise RevisionUnavailable("Current authority is unavailable") from None
        except (OSError, ValueError, TimeoutError):
            raise RevisionUnavailable("Current authority is unavailable") from None

    async def aclose(self) -> None:
        await self.channel.close()
