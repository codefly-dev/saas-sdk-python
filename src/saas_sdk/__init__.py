"""saas-sdk-python — Python SDK for the saas accounts API.

Import the facade you need:

    from saas_sdk import datasource
    ds = datasource.new(gateway)

    from saas_sdk import work_context
    verifier = work_context.JWKSVerifier("https://accounts.codefly.dev/v1/auth/.well-known/jwks.json")
    claims = verifier.verify(token, work_context.Expectations(audience="warden.evidence"))
"""

from saas_sdk import datasource, work_context

__all__ = ["datasource", "work_context"]
