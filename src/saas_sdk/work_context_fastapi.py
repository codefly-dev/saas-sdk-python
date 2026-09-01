"""FastAPI dependencies for Work Context verification — optional; install with
``saas-sdk-python[fastapi]``.

One :class:`WorkContextAuth` per service, bound to the verifier (a fixed
:class:`~saas_sdk.work_context.WorkContextVerifier` or a rotation-aware
:class:`~saas_sdk.jwks.JWKSKeySource`) and to the audience the service answers
to. It reads the ``x-codefly-work-context`` header, verifies, and exposes the
:class:`~saas_sdk.work_context.WorkContext` to the handler; ``require_scope``
layers the authorization check on top::

    from fastapi import Depends, FastAPI
    from saas_sdk import jwks, work_context as wc
    from saas_sdk.work_context_fastapi import WorkContextAuth

    auth = WorkContextAuth(jwks.JWKSKeySource.from_url(ACCOUNTS_JWKS_URL), audience="lastlogin")
    app = FastAPI()

    @app.post("/tasks/{task_id}/run")
    def run(task_id: str, ctx: wc.WorkContext = Depends(auth.require_scope("robin:tasks", "execute"))):
        return {"owner": ctx.owner_principal_id, "actor": ctx.current_actor}

Status mapping, the same split as the Go middleware in ``saas-sdk-go``:

- **401** — no carrier, a duplicated carrier, or a token that does not verify
  (signature, shape, bounds, time, issuer). Nothing about the caller is trusted.
- **403** — a *trusted* context that is not for this service (wrong ``audience``)
  or whose current actor lacks the required scope. The caller is who they say;
  they just may not do this here.

The verifier is asked to match only ``issuer``; ``audience`` is compared here
so it can land in the 403 bucket. This is the twin of ``verify_obo_token`` +
``rbac_core.require_permission`` in the callees being ported.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

try:
    from fastapi import Depends, HTTPException, Request
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        "saas_sdk.work_context_fastapi needs FastAPI; install saas-sdk-python[fastapi]"
    ) from exc

from saas_sdk.work_context import (
    ACCOUNTS_ISSUER,
    WorkContext,
    WorkContextDenied,
    WorkContextError,
    WorkContextExpectations,
    from_headers,
)

__all__ = ["Verifier", "WorkContextAuth"]

_CHALLENGE = {"WWW-Authenticate": "Codefly-Work-Context"}


class Verifier(Protocol):
    """What the dependency needs: ``WorkContextVerifier`` and ``JWKSKeySource``
    both satisfy it."""

    def verify(
        self, encoded: str, expectations: WorkContextExpectations | None = None
    ) -> WorkContext: ...


class WorkContextAuth:
    """A FastAPI dependency that yields the verified :class:`WorkContext`.

    ``audience`` is required — it is the one expectation a callee must never
    leave open. ``issuer`` defaults to what the composed accounts service mints;
    pass the exact value your deployment issues, or ``""`` to skip the check
    (not recommended).
    """

    def __init__(self, verifier: Verifier, *, audience: str, issuer: str = ACCOUNTS_ISSUER) -> None:
        if not audience:
            raise ValueError("audience is required")
        self._verifier = verifier
        self._audience = audience
        self._expectations = WorkContextExpectations(issuer=issuer)

    @property
    def audience(self) -> str:
        return self._audience

    @property
    def expectations(self) -> WorkContextExpectations:
        """What the verifier is asked to match (issuer only; audience is
        compared by the dependency itself)."""
        return self._expectations

    def __call__(self, request: Request) -> WorkContext:
        try:
            encoded = from_headers(request.headers)
            context = self._verifier.verify(encoded, self._expectations)
        except WorkContextError as exc:
            raise HTTPException(
                status_code=401, detail=f"invalid Work Context: {exc}", headers=_CHALLENGE
            ) from exc
        if context.audience != self._audience:
            raise HTTPException(
                status_code=403,
                detail=f"Work Context audience {context.audience!r} is not {self._audience!r}",
            )
        return context

    def require_scope(
        self,
        resource_kind: str,
        action: str,
        resource_id: str | Callable[[Request], str] | None = None,
        *,
        require_explicit_resource: bool = False,
    ) -> Callable[..., WorkContext]:
        """Dependency factory: verify, then demand one scope of the current
        actor. ``resource_id`` may be a fixed id or a ``Request -> str`` callable
        (e.g. reading a path parameter)."""

        def dependency(request: Request, context: WorkContext = Depends(self)) -> WorkContext:
            wanted = resource_id(request) if callable(resource_id) else resource_id
            try:
                context.require_scope(
                    resource_kind,
                    action,
                    wanted,
                    require_explicit_resource=require_explicit_resource,
                )
            except WorkContextDenied as exc:
                raise HTTPException(status_code=403, detail=f"scope denied: {exc}") from exc
            except WorkContextError as exc:
                raise HTTPException(
                    status_code=401, detail=f"invalid Work Context: {exc}", headers=_CHALLENGE
                ) from exc
            return context

        return dependency
