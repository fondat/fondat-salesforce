"""Fondat Salesforce limits module."""

from collections.abc import Iterable
from fondat.codec import get_codec, JSON, String
from fondat.data import datacls
from fondat.resource import resource, operation, query
from fondat.salesforce.client import Client
from typing import Any


@datacls
class Limit:
    Max: int
    Remaining: int


Limits = dict[str, Limit]


def limits_resource(client: Client) -> Any:
    """..."""

    path = client.resources["limits"]

    @resource
    class LimitsResource:
        """..."""

        @operation
        async def get(self) -> Limits:
            """..."""

            async with client.request(method="GET", path=f"{path}/") as response:
                return get_codec(JSON, Limits).decode(await response.json())

        @query
        async def record_count(self, sobjects: Iterable[str]) -> dict[str, int]:
            """List information about object record counts."""

            async with client.request(
                method="GET",
                path=f"{path}/recordCount",
                params={"sObjects": get_codec(String, Iterable[str]).encode(sobjects)},
            ) as response:
                json = await response.json()
                return {r["name"]: r["count"] for r in json["sObjects"]}

    return LimitsResource()
