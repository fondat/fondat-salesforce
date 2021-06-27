import pytest

import aiohttp
import asyncio
import fondat.salesforce.bulk
import fondat.salesforce.client
import fondat.salesforce.jobs
import fondat.salesforce.limits
import fondat.salesforce.oauth
import fondat.salesforce.service as service
import fondat.salesforce.sobjects
import os

from fondat.pagination import paginate


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture(scope="module")
async def authenticator():
    env = os.environ
    return fondat.salesforce.oauth.password_authenticator(
        client_id=env["FONDAT_SALESFORCE_CLIENT_ID"],
        client_secret=env["FONDAT_SALESFORCE_CLIENT_SECRET"],
        username=env["FONDAT_SALESFORCE_USERNAME"],
        password=env["FONDAT_SALESFORCE_PASSWORD"],
    )


@pytest.fixture(scope="module")
async def client(authenticator):
    async with aiohttp.ClientSession() as session:
        yield await fondat.salesforce.client.Client.create(
            session=session, version="51.0", authenticate=authenticator
        )


async def test_describe(client):
    resource = await fondat.salesforce.sobjects.sobject_resource(client=client, name="Account")
    metadata = await resource.describe()
    assert metadata.name == "Account"


async def test_resources(client):
    resources = await service.service_resource(client).resources()
    assert resources["sobjects"]


async def test_limits(client):
    limits = await fondat.salesforce.limits.limits_resource(client).get()
    assert limits


async def test_versions(client):
    versions = await fondat.salesforce.service.service_resource(client).versions()
    assert versions


async def test_sobject_get(client):
    account_id = "0015e00000BOnAVAA1"
    accounts = await fondat.salesforce.sobjects.sobject_resource(client, "Account")
    account = await accounts[account_id].get()
    assert account.Id == account_id


async def test_bulk(client):
    accounts = await fondat.salesforce.sobjects.sobject_resource(client, "Account")
    metadata = await accounts.describe()
    async with fondat.salesforce.bulk.SObjectQuery(client, metadata, fields=("Id",)) as query:
        async for row in query:
            assert row["Id"]
            break
