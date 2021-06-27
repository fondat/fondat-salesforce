"""Fondat Salesforce sObject module."""

from datetime import date, datetime
from fondat.codec import JSON, get_codec
from fondat.data import datacls, make_datacls
from fondat.resource import resource, operation, query
from fondat.salesforce.client import Client
from fondat.validation import MaxLen
from typing import Annotated, Any, Literal, Optional


@datacls
class PicklistEntry:
    active: bool
    label: Optional[str]
    value: str


@datacls
class Location:
    latitude: Optional[float]
    longitude: Optional[float]


@datacls
class Address(Location):
    accuracy: Optional[str]
    city: Optional[str]
    country: Optional[str]
    countryCode: Optional[str]
    postalCode: Optional[str]
    state: Optional[str]
    stateCode: Optional[str]
    street: Optional[str]


_type_mappings = {
    "address": Address,
    "anyType": Any,
    "base64": bytes,
    "boolean": bool,
    "combobox": str,
    "currency": float,
    "date": date,
    "datetime": datetime,
    "double": float,
    "email": str,
    "encryptedstring": str,
    "id": str,
    "int": int,
    "location": Location,
    "multipicklist": str,
    "percent": float,
    "phone": str,
    "picklist": str,
    "reference": str,
    "time": str,
    "string": str,
    "textarea": str,
    "url": str,
}


FieldType = Literal[tuple(_type_mappings.keys())]


@datacls
class Field:
    name: str
    type: FieldType
    label: Optional[str]
    nillable: bool
    length: int
    picklistValues: list[PicklistEntry]
    unique: bool
    custom: bool


@datacls
class SObjectMetadata:
    name: str
    fields: list[Field]


def sobject_field_type(field: Field) -> Any:
    """Return the Python type associated with an SObject field."""

    try:
        result = _type_mappings[field.type]
    except KeyError:
        raise TypeError(f"unsupported field type: {field.type}")
    if field.length != 0:
        result = Annotated[result, MaxLen(field.length)]
    if field.nillable:
        result = Optional[result]
    return result


@datacls
class SObjectURLs:
    sobject: str
    describe: str
    rowTemplate: str


async def sobject_resource(client: Client, name: str):
    """..."""

    path = f"{client.resources['sobjects']}/{name}"

    async with client.request(method="GET", path=f"{path}/describe/") as response:
        metadata = get_codec(JSON, SObjectMetadata).decode(await response.json())

    datacls = make_datacls(
        f"{metadata.name}Resource",
        [(field.name, sobject_field_type(field)) for field in metadata.fields],
    )

    codec = get_codec(JSON, datacls)

    @resource
    class SObjectRowResource:
        """..."""

        def __init__(self, id: str):
            self.id = id

        @operation
        async def get(self) -> datacls:
            async with client.request(method="GET", path=f"{path}/{self.id}/") as response:
                return codec.decode(await response.json())

    @resource
    class SObjectResource:
        """..."""

        @query
        async def describe(self) -> SObjectMetadata:
            return metadata

        def __getitem__(self, id) -> SObjectRowResource:
            return SObjectRowResource(id)

    return SObjectResource()


@datacls
class SObject:
    activateable: bool
    custom: bool
    customSetting: bool
    createable: bool
    deletable: bool
    deprecatedAndHidden: bool
    feedEnabled: bool
    keyPrefix: str
    label: str
    labelPlural: str
    layoutable: bool
    mergeable: bool
    mruEnabled: bool
    name: str
    queryable: bool
    replicateable: bool
    retrieveable: bool
    searchable: bool
    triggerable: bool
    undeletable: bool
    updateable: bool
    urls: SObjectURLs


@datacls
class SObjects:
    encoding: str
    maxBatchSize: int
    sobjects: list[SObject]


def sobjects_resource(client: Client):
    """..."""

    path = f"{client.resources['sobjects']}/"

    @resource
    class SObjectsResource:
        """..."""

        @operation
        async def get(self) -> list[SObject]:
            """Get a list of objects."""
            async with client.request(method="GET", path=path) as response:
                return get_codec(JSON, list[SObject]).decode(await response.json())

    return SObjectsResource()
