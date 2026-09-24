"""saas-sdk-python — Python SDK for the saas accounts API.

Import the facade you need:

    from saas_sdk import datasource
    ds = datasource.new(gateway)

`audit` reads the organization's audit trail as the signed-in person:

    from saas_sdk import audit
    log = audit.new(gateway)

`work_context` carries both halves of the Work Context feature. Mint side, a
delegated caller stamps a signed context on outgoing calls:

    from saas_sdk import work_context
    wc = work_context.new(gateway)

Callee side, a service verifies a presented context:

    verifier = work_context.JWKSVerifier("https://accounts.codefly.dev/v1/auth/.well-known/jwks.json")
    claims = verifier.verify(token, work_context.Expectations(audience="warden.evidence"))
"""

from saas_sdk import audit, datasource, work_context

__all__ = ["audit", "datasource", "work_context"]
