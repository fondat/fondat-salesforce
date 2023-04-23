import aiohttp
import asyncio
import contextlib
import fondat.salesforce.bulk
import fondat.salesforce.client
import fondat.salesforce.jobs
import fondat.salesforce.limits
import fondat.salesforce.oauth
import fondat.salesforce.service as service
import fondat.salesforce.sobjects
import os
import pytest

from fondat.error import NotFoundError
from fondat.salesforce.bulk import SObjectQuery
from pytest import fixture


VERSION = "57.0"


@fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _password_authenticator():
    env = os.environ
    return fondat.salesforce.oauth.password_authenticator(
        endpoint="https://login.salesforce.com",
        client_id=env["FONDAT_SALESFORCE_CLIENT_ID"],
        client_secret=env["FONDAT_SALESFORCE_CLIENT_SECRET"],
        username=env["FONDAT_SALESFORCE_USERNAME"],
        password=env["FONDAT_SALESFORCE_PASSWORD"],
    )


@pytest.fixture(scope="module")
def password_authenticator():
    return _password_authenticator()


@pytest.fixture(scope="module")
def refresh_authenticator():
    env = os.environ
    return fondat.salesforce.oauth.refresh_authenticator(
        endpoint="https://login.salesforce.com",
        client_id=env["FONDAT_SALESFORCE_CLIENT_ID"],
        client_secret=env["FONDAT_SALESFORCE_CLIENT_SECRET"],
        refresh_token=env["FONDAT_SALESFORCE_REFRESH_TOKEN"],
    )


@contextlib.asynccontextmanager
async def _client(authenticator):
    async with aiohttp.ClientSession() as session:
        yield await fondat.salesforce.client.Client.create(
            session=session, version=VERSION, authenticate=authenticator
        )


@pytest.fixture(scope="module")
async def client(refresh_authenticator):
    async with _client(refresh_authenticator) as client:
        yield client


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


async def test_record_count(client):
    limits = fondat.salesforce.limits.limits_resource(client)
    counts = await limits.record_count(["Account", "Opportunity"])
    assert counts["Account"] > 0
    assert counts["Opportunity"] > 0


async def test_versions(client):
    versions = await fondat.salesforce.service.service_resource(client).versions()
    assert versions


async def test_sobject_get(client):
    account_id = "0015e00000BOnAVAA1"
    accounts = await fondat.salesforce.sobjects.sobject_data_resource(client, "Account")
    account = await accounts[account_id].get()
    assert account.Id == account_id


async def test_bulk_fields(client):
    accounts = await fondat.salesforce.sobjects.sobject_data_resource(client, "Account")
    sobject = await accounts.describe()
    async with SObjectQuery(
        client, sobject, columns={"Id", "Name", "Website"}, order_by="Name, Website"
    ) as query:
        async for row in query:
            assert row["Id"]
            break


async def test_bulk_limit(client):
    accounts = await fondat.salesforce.sobjects.sobject_data_resource(client, "Account")
    sobject = await accounts.describe()
    count = 0
    async with SObjectQuery(client, sobject, limit=1) as query:
        async for row in query:
            count += 1
    assert count == 1


async def test_bulk_columns(client):
    opportunities = await fondat.salesforce.sobjects.sobject_data_resource(
        client, "Opportunity"
    )
    sobject = await opportunities.describe()
    async with SObjectQuery(
        client,
        sobject,
        columns={"Id", SObjectQuery.Column("Amount", "FORMAT(amount)", str)},
        limit=1,
    ) as query:
        async for row in query:
            assert row["Id"]
            assert row["Amount"]
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


# async def test_password_authenticator():
#     async with _client(_password_authenticator()) as client:
#         assert await fondat.salesforce.service.service_resource(client).versions()


# async def test_sobjects_describe_all(client):
#     sobjects = fondat.salesforce.sobjects.sobjects_metadata_resource(client)
#     for name in [sobject.name for sobject in (await sobjects.get()).sobjects]:
#         await sobjects[name].describe()
