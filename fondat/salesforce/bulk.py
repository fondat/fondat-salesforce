"""Fondat Salesforce bulk module."""

import asyncio

from contextlib import suppress
from collections import deque
from collections.abc import Sequence
from fondat.csv import typeddict_codec
from fondat.salesforce.client import Client
from fondat.salesforce.sobjects import SObject, sobject_field_type
from fondat.salesforce.jobs import queries_resource
from typing import Any, TypedDict


_exclude_types = {"address", "location"}


class SObjectQuery:
    """..."""

    def __init__(
        self,
        client: Client,
        sobject: SObject,
        fields: Sequence[str] = None,
        where: str = None,
        order: Sequence[str] = None,
        page_size: int = None,
    ):
        self.client = client
        self.page_size = page_size
        indexed = {field.name: field for field in sobject.fields}
        if fields is None:
            fields = [f.name for f in sobject.fields if f.type not in _exclude_types]
        if len(fields) == 0:
            raise ValueError("you must query at least one field")
        for name in fields:
            if not (field := indexed.get(name)):
                raise ValueError(f"unknown field: {name}")
            if field.type in _exclude_types:
                raise ValueError(f"cannot query {field.type} type field: {name}")
        self.td = TypedDict("QueryDict", {f: sobject_field_type(indexed[f]) for f in fields})
        self.stmt = f"SELECT {', '.join(fields)} FROM {sobject.name}"
        if where:
            self.stmt += f" WHERE {where}"
        if order:
            self.stmt += f" ORDER BY {', '.join(order)}"
        self.query = None
        self.results = None
        self.header = None
        self.cursor = None

    async def info(self):
        return await self.query.get()

    async def _await_complete(self):
        """Wait for job to be complete."""
        while (state := (await self.info()).state) in {"UploadComplete", "InProgress"}:
            await asyncio.sleep(1)  # TODO: timeout
        if state != "JobComplete":
            raise RuntimeError(f"unexpected job state: {state}")

    async def __aenter__(self):
        if self.query is not None:
            raise RuntimeError("context is not reentrant")
        queries = queries_resource(self.client)
        info = await queries.post(operation="query", query=self.stmt)
        self.query = queries[info.id]
        return self

    async def __aexit__(self, *args):
        if self.results is None:
            await self._await_complete()
        with suppress(Exception):
            await self.query.delete()

    def __aiter__(self):
        if self.query is None:
            raise RuntimeError("must iterate within async context")
        return self

    async def _next_page(self):
        page = await self.query.results(limit=self.page_size or 1000, cursor=self.cursor)
        self.results = deque(page.items)
        self.cursor = page.cursor
        self.codec = typeddict_codec(self.td, self.results.popleft())

    async def __anext__(self) -> dict[str, Any]:
        if self.results is None:
            await self._await_complete()
        if self.results is None or (not self.results and self.cursor):
            await self._next_page()
        if not self.results and not self.cursor:
            raise StopAsyncIteration
        return self.codec.decode(self.results.popleft())
