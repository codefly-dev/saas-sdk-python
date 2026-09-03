"""Mint-side client for the saas ``WorkContextService`` — the Python twin of
``sdk-go``'s Work Context authority helpers, and the delegated-caller companion
to the verifier.

A solution acting on a user's behalf mints a short-lived Codefly Work Context at
turn start and stamps it on every outgoing call, so a downstream service can
verify the delegated authority instead of trusting the caller:

    from saas_sdk import work_context

    wc = work_context.new(gateway)
    parent = wc.start_task(
        bearer=user_bearer,
        org_id=org,
        task_id=task,
        session_id=session,
        audience="accounts",
        scopes=[work_context.pb.WorkContextScope(resource_kind="evidence", actions=["read"])],
    )
    for callee in ("accounts", "evidence"):
        ctx = wc.exchange_audience(bearer=user_bearer, parent=parent, audience=callee, scopes=parent_scopes)
        wc.attach(headers, ctx)          # per outgoing request to `callee`

Every mint RPC is owner-bound: the accounts service authorizes the call against
the *user's* identity, so the user's bearer is passed explicitly on each call
rather than relying on the gateway's ambient service identity. ``renew`` is the
one exception — its caller is the current actor of the context (the delegated
task itself), which lets long-running work extend past the TTL cap while the
user is offline; pass that actor's bearer there.

TTL follows the sdk-go authority defaults: a context lives 5 minutes by default
and at most 15 minutes per issuance (:data:`DEFAULT_TTL` / :data:`MAX_TTL`).
Run past that cap by minting a fresh context with ``renew``.
"""

from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from datetime import timedelta
from typing import Protocol, TypeVar

from saas_sdk._gen import work_contexts_pb2 as pb

__all__ = [
    "Client",
    "Gateway",
    "WorkContextMintError",
    "DEFAULT_TTL",
    "MAX_TTL",
    "HEADER_NAME",
    "new",
    "pb",
]

_M = TypeVar("_M")

_SERVICE = "/saas.accounts.v1.WorkContextService/"

# The lone HTTP carrier for a signed Work Context; wire-identical to sdk-go's
# WorkContextHeaderName. Callers stamp it through ``attach`` rather than naming
# it directly.
HEADER_NAME = "x-codefly-work-context"

# Issuance TTL bounds, matching sdk-go's WorkContextDefaultTTL / WorkContextMaxTTL.
DEFAULT_TTL = timedelta(minutes=5)
MAX_TTL = timedelta(minutes=15)

# sdk-go bounds a token at 32 KiB and requires exactly the two base64url
# segments of `payload.signature`; a malformed token is never stamped.
_MAX_TOKEN_BYTES = 32 * 1024


class WorkContextMintError(Exception):
    """A mint RPC (``StartTask`` / ``ExchangeAudience`` / ``RenewWorkContext``)
    was rejected or failed at the accounts service.

    Distinct from a verification failure so a delegated caller that both mints
    and verifies can tell a minting problem (this side) from a bad presented
    capability (the verify side).
    """

    def __init__(self, procedure: str, cause: object) -> None:
        self.procedure = procedure
        super().__init__(f"{procedure}: {cause}")


class Gateway(Protocol):
    """Transport seam the mint client needs from the solution runtime.

    Unlike the ambient-auth datasource gateway, ``unary`` takes the ``bearer``
    to present as the call's authorization, so the mint client can bind each
    owner-bound RPC to the user's token rather than the solution's own identity.
    """

    def unary(self, procedure: str, request, response_type: type[_M], *, bearer: str) -> _M: ...


class Client:
    """Entry point: ``new(gateway).start_task(...)``."""

    def __init__(self, gateway: Gateway) -> None:
        self._gateway = gateway

    def start_task(
        self,
        *,
        bearer: str,
        org_id: str,
        task_id: str,
        session_id: str,
        audience: str,
        scopes: Sequence[pb.WorkContextScope],
        actor_principal_id: str = "",
        ttl: timedelta | None = None,
        replay_policy: pb.WorkContextReplayPolicy = pb.WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED,
        workspace_id: str = "",
        project_id: str = "",
    ) -> pb.IssuedWorkContext:
        """Mint the root capability for a task and return the issued context.

        ``actor_principal_id`` empty means a direct human-owned task; otherwise
        it names the agent principal acting under the user's authority.
        """
        request = pb.StartTaskWorkContextRequest(
            org_id=org_id,
            task_id=task_id,
            session_id=session_id,
            audience=audience,
            authority_scopes=list(scopes),
            replay_policy=replay_policy,
            ttl_seconds=_ttl_seconds(ttl),
        )
        if actor_principal_id:
            request.actor_principal_id = actor_principal_id
        if workspace_id:
            request.workspace_id = workspace_id
        if project_id:
            request.project_id = project_id
        return self._mint("StartTask", request, bearer)

    def exchange_audience(
        self,
        *,
        bearer: str,
        parent: pb.IssuedWorkContext,
        audience: str,
        scopes: Sequence[pb.WorkContextScope],
        ttl: timedelta | None = None,
        replay_policy: pb.WorkContextReplayPolicy = pb.WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED,
    ) -> pb.IssuedWorkContext:
        """Reissue ``parent`` for one callee ``audience``, attenuating authority
        to ``scopes`` — the same task, session, and owner, never widened. Call
        once per distinct callee audience at turn start.
        """
        request = pb.ExchangeWorkContextAudienceRequest(
            org_id=parent.org_id,
            parent_work_context_token=parent.token,
            audience=audience,
            attenuated_scopes=list(scopes),
            replay_policy=replay_policy,
            ttl_seconds=_ttl_seconds(ttl),
        )
        return self._mint("ExchangeAudience", request, bearer)

    def renew(
        self,
        *,
        bearer: str,
        ctx: pb.IssuedWorkContext,
        audience: str | None = None,
        scopes: Sequence[pb.WorkContextScope] = (),
        ttl: timedelta | None = None,
        replay_policy: pb.WorkContextReplayPolicy = pb.WORK_CONTEXT_REPLAY_POLICY_UNSPECIFIED,
    ) -> pb.IssuedWorkContext:
        """Extend ``ctx`` with a fresh TTL for work running past the cap, using
        the current actor's ``bearer`` rather than the owner's.

        ``audience`` ``None`` keeps the parent's audience (the common
        TTL-only refresh); empty ``scopes`` keeps the actor's authority
        unchanged. Neither can widen the current actor's authority.
        """
        request = pb.RenewWorkContextRequest(
            org_id=ctx.org_id,
            parent_work_context_token=ctx.token,
            replay_policy=replay_policy,
            ttl_seconds=_ttl_seconds(ttl),
        )
        if audience is not None:
            request.audience = audience
        if scopes:
            request.attenuated_scopes.extend(scopes)
        return self._mint("RenewWorkContext", request, bearer)

    @staticmethod
    def attach(request_or_headers: _Headers, ctx: pb.IssuedWorkContext) -> _Headers:
        """Stamp ``ctx``'s token on an outgoing call and return the target.

        ``request_or_headers`` is either a mutable header mapping or a request
        object exposing one as ``.headers``.
        """
        headers = getattr(request_or_headers, "headers", request_or_headers)
        headers[HEADER_NAME] = _validated_token(ctx.token)
        return request_or_headers

    def _mint(self, method: str, request, bearer: str) -> pb.IssuedWorkContext:
        try:
            return self._gateway.unary(
                _SERVICE + method, request, pb.IssuedWorkContext, bearer=bearer
            )
        except WorkContextMintError:
            raise
        except Exception as err:  # transport / RPC failure — surface it as a mint error
            raise WorkContextMintError(method, err) from err


_Headers = MutableMapping[str, str]


def _ttl_seconds(ttl: timedelta | None) -> int:
    resolved = DEFAULT_TTL if ttl is None else ttl
    seconds = round(resolved.total_seconds())
    if not 0 < seconds <= round(MAX_TTL.total_seconds()):
        raise ValueError(f"ttl must be in (0, {MAX_TTL}]; got {resolved}")
    return seconds


def _validated_token(token: str) -> str:
    if not token:
        raise ValueError("work context token is empty")
    if len(token.encode()) > _MAX_TOKEN_BYTES:
        raise ValueError("work context token exceeds 32 KiB")
    if token.count(".") != 1:
        raise ValueError("work context token must have exactly two segments")
    return token


def new(gateway: Gateway) -> Client:
    """Bind the mint-side Work Context client to a solution runtime gateway."""
    return Client(gateway)
