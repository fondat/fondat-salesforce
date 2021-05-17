"""Module to asynchronously query large data sets."""

import asyncio
import http

from collections.abc import Iterable
from datetime import datetime
from fondat.codec import get_codec, JSON, String
from fondat.data import datacls
from fondat.error import reraise, InternalServerError
from fondat.resource import resource, operation, query
from fondat.salesforce.client import Client
from typing import Literal, Optional


Operation = Literal["query", "queryAll"]
ContentType = Literal["CSV"]
LineEnding = Literal["LF", "CRLF"]
ColumnDelimiter = Literal["BACKQUOTE", "CARET", "COMMA", "PIPE", "SEMICOLON", "TAB"]
QueryState = Literal["UploadComplete", "InProgress", "Aborted", "JobComplete", "Failed"]
ConcurrencyMode = Literal["Parallel"]


@datacls
class Query:
    id: str
    operation: Operation
    object: str
    createdById: str
    createdDate: datetime
    systemModStamp: Optional[datetime]
    state: QueryState
    concurrencyMode: ConcurrencyMode
    contentType: ContentType
    apiVersion: float
    jobType: Optional[str]
    lineEnding: LineEnding
    columnDelimiter: ColumnDelimiter
    numberRecordsProcessed: Optional[int]
    retries: Optional[int]
    totalProcessingTime: Optional[int]


@datacls
class QueryResultsPage:
    items: list[dict[str, str]]
    cursor: Optional[bytes]


@datacls
class QueriesPage:
    items: list[Query]
    cursor: Optional[bytes]


@datacls
class _QueriesResponse:
    done: bool
    records: list[Query]
    nextRecordsUrl: Optional[str]


@datacls
class _CreateQueryRequest:
    operation: Operation
    query: str
    contentType: Optional[ContentType]
    columnDelimiter: Optional[ColumnDelimiter]
    lineEnding: Optional[LineEnding]


def queries_resource(client: Client):
    """Create asynchronous jobs resource."""

    path = f"{client.resources['jobs']}/query"

    @resource
    class QueryResource:
        """Asynchronous query job."""

        def __init__(self, id: str):
            self.path = f"{path}/{id}"

        @operation
        async def get(self) -> Query:
            """Get information about a query job."""

            async with client.request("GET", self.path) as response:
                with reraise((TypeError, ValueError), InternalServerError):
                    return get_codec(JSON, Query).decode(await response.json())

        @operation
        async def delete(self):
            """Delete a query job."""

            async with client.request("DELETE", self.path):
                pass

        @query
        async def results(self, limit: int = None, cursor: bytes = None) -> QueryResultsPage:
            """Get results for a query job."""

            params = {"maxRecords": str(limit or 10000)}
            if cursor:
                params["locator"] = cursor.decode()
            async with client.request(
                method="GET",
                path=f"{self.path}/results",
                headers={"Accept": "text/csv"},
                params=params,
            ) as response:
                if response.status == http.HTTPStatus.NO_CONTENT.value:
                    await asyncio.sleep(1)
                    return QueryResultsPage(items=[], cursor=b"")
                row_codec = get_codec(String, list[str])
                items = []
                keys = row_codec.decode((await response.content.readline()).decode())
                while line := (await response.content.readline()).decode():
                    items.append(dict(zip(keys, row_codec.decode(line))))
                locator = response.headers.get("Sforce-Locator")
            return QueryResultsPage(
                items=items, cursor=locator.encode() if locator and locator != "null" else None
            )

    @resource
    class QueriesResource:
        """Asynchronous query jobs."""

        @operation
        async def get(self, cursor: bytes = None) -> QueriesPage:
            """Get information about all query jobs."""

            params = {"jobType": "V2Query"}
            try:
                async with client.request(
                    method="GET", path=cursor.decode() if cursor else path, params=params
                ) as response:
                    json = get_codec(JSON, _QueriesResponse).decode(await response.json())
            except (TypeError, ValueError) as e:
                raise InternalServerError from e
            return QueriesPage(
                items=json.records,
                cursor=json.nextRecordsUrl.encode() if json.nextRecordsUrl else None,
            )

        @operation
        async def post(self, operation: Operation, query: str) -> Query:
            """Create a query job."""

            request = _CreateQueryRequest(operation=operation, query=query)
            async with client.request(
                method="POST",
                path=f"{path}/",
                json=get_codec(JSON, _CreateQueryRequest).encode(request),
            ) as response:
                return get_codec(JSON, Query).decode(await response.json())

        def __getitem__(self, id: str) -> QueryResource:
            return QueryResource(id)

    return QueriesResource()
