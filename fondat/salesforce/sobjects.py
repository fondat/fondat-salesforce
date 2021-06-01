"""..."""

from collections.abc import Iterable
from datetime import date, datetime
from fondat.codec import JSON, get_codec
from fondat.data import datacls, make_datacls
from fondat.resource import resource, operation, query
from fondat.salesforce.client import Client
from fondat.security import Policy
from fondat.validation import MaxLen
from typing import Annotated, Any, Literal, Optional


FieldType = Literal[
    "id",
    "string",
    "int",
    "double",
    "boolean",
    "date",
    "datetime",
    "base64",
    "reference",
    "currency",
    "textarea",
    "percent",
    "phone",
    "url",
    "email",
    "combobox",
    "picklist",
    "multipicklist",
    "anyType",
    "location",
    "address",
]


@datacls
class PicklistEntry:
    active: bool
    label: str
    value: str


@datacls
class Address:
    geocodeAccuracy: Optional[str]
    city: Optional[str]
    country: Optional[str]
    countryCode: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    postalCode: Optional[str]
    state: Optional[str]
    stateCode: Optional[str]
    street: Optional[str]


@datacls
class Field:
    name: str
    type: FieldType
    label: str
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

    if field.type in {"email", "id", "reference", "phone", "string", "textarea", "url"}:
        result = str
    elif field.type == "int":
        result = int
    elif field.type in {"currency", "double", "percent"}:
        result = float
    elif field.type == "boolean":
        result = bool
    elif field.type == "date":
        result = date
    elif field.type == "datetime":
        result = datetime
    elif field.type == "base64":
        result = bytes
    elif field.type == "picklist":
        result = Literal[tuple(entry.value for entry in field.picklistValues)]
    elif field.type == "address":
        result = Address
    else:
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
