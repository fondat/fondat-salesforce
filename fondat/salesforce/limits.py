"""Fondat Salesforce limits module."""

from fondat.codec import get_codec, JSON
from fondat.data import datacls
from fondat.error import reraise, InternalServerError
from fondat.resource import operation, resource
from fondat.salesforce.client import Client
from typing import Any


@datacls
class Limit:
    Max: int
    Remaining: int


Limits = dict[str, Limit]


def limits_resource(client: Client) -> Any:
    """..."""

    path = f"{client.resources['limits']}/"

    @resource
    class LimitsResource:
        """..."""

        @operation
        async def get(self) -> Limits:
            """..."""

            async with client.request(method="GET", path=path) as response:
                with reraise((TypeError, ValueError), InternalServerError):
                    return get_codec(JSON, Limits).decode(await response.json())

    return LimitsResource()
