"""saas-sdk-python — Python SDK for the saas accounts API.

Import the gateway-bound facade you need:

    from saas_sdk import datasource
    ds = datasource.new(gateway)

    from saas_sdk import work_context
    wc = work_context.new(gateway)
"""

from saas_sdk import datasource, work_context

__all__ = ["datasource", "work_context"]
