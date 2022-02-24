"""Fondat Salesforce client module."""

import aiohttp
import fondat.error
import logging

from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any, Optional


_logger = logging.getLogger(__name__)


class Client:
    """
    Salesforce API client.

    Parameters:
    • session: client session to use for HTTP requests
    • version: API version to use; example: "51.0"
    • authenticate: coroutine function to authenticate and return a token
    """

    @classmethod
    async def create(
        cls,
        *,
        session: aiohttp.ClientSession,
        version: str,
        authenticate: Callable[[], Coroutine[Any, Any, Any]],
    ):
        from fondat.salesforce.service import service_resource

        self = cls()
        self.session = session
        self.version = version
        self.authenticate = authenticate
        self.token = None
        self.resources = await service_resource(self).resources()
        return self

    def path(self, resource: str) -> str:
        """Return path to the specified resource."""
        try:
            return self.resources[resource]
        except KeyError:
            raise fondat.error.NotFoundError(f"unknown resource: {resource}")

    @asynccontextmanager
    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, str]] = None,
        json: Any = None,
    ) -> Any:
        """..."""

        headers = {"Accept": "application/json", "Accept-Encoding": "gzip"} | (headers or {})

        for retry in range(2):  # retry for token refresh
            if not self.token:
                self.token = await self.authenticate(self.session)
            headers["Authorization"] = f"Bearer {self.token.access_token}"
            url = f"{self.token.instance_url}{path}"
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    compress=bool(json),
                ) as response:
                    _logger.debug("%s %s %d", method, url, response.status)
                    if 400 <= response.status <= 599:
                        raise fondat.error.errors[response.status](await response.text())
                    elif 200 <= response.status <= 299:
                        yield response
                        return
                    else:
                        raise fondat.error.InternalServerError(
                            f"unexpected response: {response.status} {await response.text()}"
                        )
            except fondat.error.UnauthorizedError:
                if retry:
                    raise
                _logger.debug("unauthorized; retrying authentication")
                self.token = None
