"""Typed, gateway-bound client facade for the saas ``DatasourceService`` — the
"connection" half of datasource ingestion, and the Python twin of
``saas-sdk-go``'s ``datasource`` package.

It is the syntactic-sugar layer over the generated protobuf message types: it
names the Connect procedure and routes every call through the solution runtime's
``Gateway.unary(procedure, request, response_type)`` seam (which owns transport,
auth, and the wire protocol), so a solution connects a GitHub datasource
collection in a few lines::

    from datasource import new

    ds = new(gateway)
    source = ds.add_github_source(
        org_id=org,
        repo="codefly-dev/module-saas-starter",
        paths=["docs"],
        collection="handbook",
        access_token=token,
    )
    ds.sync_source(org, source.id)

The access token is sent once; the connection side encrypts it and persists only
a secret reference — no read ever returns it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar

from saas.accounts.v1 import datasource_pb2 as pb

__all__ = ["Client", "Gateway", "new", "pb"]

_M = TypeVar("_M")

_SERVICE = "/saas.accounts.v1.DatasourceService/"


class Gateway(Protocol):
    """Minimal surface this SDK needs from the solution runtime.

    ``solution_runtime.Gateway`` satisfies it as-is: it forwards the caller's
    bearer and owns the Connect transport, so this package stays transport- and
    auth-agnostic.
    """

    def unary(self, procedure: str, request, response_type: type[_M]) -> _M: ...


class Client:
    """Entry point: ``new(gateway).add_github_source(...)``."""

    def __init__(self, gateway: Gateway) -> None:
        self._gateway = gateway

    def add_github_source(
        self,
        *,
        org_id: str,
        repo: str,
        collection: str,
        access_token: str,
        paths: Sequence[str] = (),
        branch: str = "",
        webhook_secret: str = "",
    ) -> pb.Datasource:
        """Register a GitHub repository as a datasource and return the non-secret
        projection the server stored."""
        request = pb.AddGitHubSourceRequest(
            org_id=org_id,
            repo=repo,
            paths=list(paths),
            branch=branch,
            target_collection=collection,
            access_token=access_token,
            webhook_secret=webhook_secret,
        )
        response = self._gateway.unary(
            _SERVICE + "AddGitHubSource", request, pb.AddGitHubSourceResponse
        )
        return response.datasource

    def list_sources(self, org_id: str) -> list[pb.Datasource]:
        """Return the org's connected datasources."""
        response = self._gateway.unary(
            _SERVICE + "ListSources", pb.ListSourcesRequest(org_id=org_id), pb.ListSourcesResponse
        )
        return list(response.datasources)

    def get_source(self, org_id: str, id: str) -> pb.Datasource:
        """Return one connected datasource in the org."""
        response = self._gateway.unary(
            _SERVICE + "GetSource", pb.GetSourceRequest(org_id=org_id, id=id), pb.GetSourceResponse
        )
        return response.datasource

    def sync_source(self, org_id: str, id: str) -> str:
        """Mark a source for ingestion and return the durable jobs-inbox id of
        the enqueued request."""
        response = self._gateway.unary(
            _SERVICE + "SyncSource", pb.SyncSourceRequest(org_id=org_id, id=id), pb.SyncSourceResponse
        )
        return response.job_id

    def delete_source(self, org_id: str, id: str) -> None:
        """Remove a connected datasource and its stored credentials."""
        self._gateway.unary(
            _SERVICE + "DeleteSource",
            pb.DeleteSourceRequest(org_id=org_id, id=id),
            pb.DeleteSourceResponse,
        )


def new(gateway: Gateway) -> Client:
    """Bind the datasource SDK to a solution runtime gateway."""
    return Client(gateway)
