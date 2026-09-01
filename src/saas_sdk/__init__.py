"""saas-sdk-python — Python SDK for the saas accounts API.

Import the gateway-bound facade you need; today that is `datasource`:

    from saas_sdk import datasource
    ds = datasource.new(gateway)

Callee-side Work Context verification lives in `work_context` (the verifier)
and `jwks` (key discovery from the accounts JWKS); the optional FastAPI
dependency is in `work_context_fastapi` and needs the `fastapi` extra.

    from saas_sdk import jwks, work_context
"""

from saas_sdk import datasource, jwks, work_context

__all__ = ["datasource", "jwks", "work_context"]
