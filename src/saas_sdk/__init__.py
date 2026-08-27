"""saas-sdk-python — Python SDK for the saas accounts API.

Import the gateway-bound facade you need; today that is `datasource`:

    from saas_sdk import datasource
    ds = datasource.new(gateway)
"""

from saas_sdk import datasource

__all__ = ["datasource"]
