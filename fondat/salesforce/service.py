"""Fondat Salesforce service module."""

import fondat.error

from fondat.codec import get_codec, JSON
from fondat.data import datacls
from fondat.error import InternalServerError, NotFoundError
from fondat.resource import resource, query
from fondat.salesforce.client import Client


@datacls
class Limit:
    Max: int
    Remaining: int


Limits = dict[str, Limit]


@datacls
class Version:
    label: str
    url: str
    version: str


def service_resource(client: Client):
    """..."""

    @resource
    class ServiceResource:
        """..."""

        @query
        async def resources(self) -> dict[str, str]:
            """List available REST resources."""

            for version in await self.versions():
                if version.version == client.version:
                    async with client.request(
                        method="GET", path=f"/{version.url}/"
                    ) as response:
                        return await response.json()
            raise NotFoundError(f"unknown version: {client.version}")

        @query
        async def versions(self) -> list[Version]:
            """List available REST API versions."""

            async with client.request(method="GET", path="/services/data/") as response:
                return get_codec(JSON, list[Version]).decode(await response.json())

    return ServiceResource()
