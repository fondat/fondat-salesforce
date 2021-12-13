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

from fondat.error import NotFoundError
from fondat.pagination import paginate


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def event_loop():
    return asyncio.new_event_loop()


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
            session=session, version="52.0", authenticate=authenticator
        )


async def test_sobject_metadata(client):
    resource = await fondat.salesforce.sobjects.sobject_data_resource(
        client=client, name="Account"
    )
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
    accounts = await fondat.salesforce.sobjects.sobject_data_resource(client, "Account")
    account = await accounts[account_id].get()
    assert account.Id == account_id


async def test_bulk(client):
    accounts = await fondat.salesforce.sobjects.sobject_data_resource(client, "Account")
    metadata = await accounts.describe()
    async with fondat.salesforce.bulk.SObjectQuery(
        client, metadata, fields=("Id", "Name", "Website"), order=("Name", "Website")
    ) as query:
        async for row in query:
            assert row["Id"]
            break


async def test_invalid_sobject(client):
    with pytest.raises(TypeError):
        await fondat.salesforce.sobjects.sobject_data_resource(client, "account")  # lower case


async def test_sobjects_describe_global(client):
    await fondat.salesforce.sobjects.sobjects_metadata_resource(client).get()


async def test_sobjects_describe_common(client):
    sobjects = fondat.salesforce.sobjects.sobjects_metadata_resource(client)
    await sobjects["Account"].describe()
    await sobjects["Contact"].describe()
    await sobjects["Lead"].describe()
    await sobjects["Opportunity"].describe()
    await sobjects["Product2"].describe()


async def test_invalid_sobjects_metadata(client):
    sobjects = fondat.salesforce.sobjects.sobjects_metadata_resource(client)
    with pytest.raises(NotFoundError):
        await sobjects["account"].describe()  # lower case


# async def test_sobjects_describe_all(client):
#     sobjects = fondat.salesforce.sobjects.sobjects_metadata_resource(client)
#     for name in [sobject.name for sobject in (await sobjects.get()).sobjects]:
#         await sobjects[name].describe()
