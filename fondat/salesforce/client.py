"""Fondat Salesforce client module."""

import aiohttp
import asyncio
import fondat.error
import logging

from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any, Literal


_logger = logging.getLogger(__name__)


class Client:
    """
    Salesforce API client.

    """

    @classmethod
    async def create(
        cls,
        *,
        session: aiohttp.ClientSession,
        version: str,
        authenticate: Callable[[], Coroutine[Any, Any, Any]],
        retries: int = 3,
    ):
        """
        Create a Salesforce API client.

        Parameters:
        • session: client session to use to make HTTP requests
        • version: API version to use; example: "54.0"
        • authenticate: coroutine function to authenticate and return an access token
        • retries: number of times to retry server errors

        Server error retries backoff exponentially.
        """

        from fondat.salesforce.service import service_resource  # avoid circular dependencies

        self = cls()
        self.session = session
        self.version = version
        self.authenticate = authenticate
        self.retries = retries
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
        method: Literal["GET", "PUT", "POST", "DELETE", "PATCH"],
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        json: Any = None,
    ) -> Any:
        """
        Make an HTTP request to a Salesforce API resource.

        Parameters:
        • method: HTTP request method
        • path: request path, relative to instance URL
        • headers: HTTP headers to include in request
        • params: query parameters to include in request
        • json: JSON body data to include in request
        """

        headers = {"Accept": "application/json", "Accept-Encoding": "gzip"} | (headers or {})

        auth_error = False
        server_errors = 0

        while True:
            if not self.token:
                self.token = await self.authenticate(self.session)
            headers["Authorization"] = f"Bearer {self.token.access_token}"
            url = f"{self.token.instance_url}{path}"
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                compress=bool(json),
            ) as response:
                _logger.debug("%s %s %d", method, url, response.status)
                if 200 <= response.status <= 299:
                    yield response
                    return
                elif response.status == 401 and not auth_error:  # only retry once
                    _logger.debug("retrying authentication")
                    auth_error = True
                    token = None
                    continue
                elif 500 <= response.status <= 599 and server_errors < self.retries:
                    _logger.debug(f"retrying server error")
                    await asyncio.sleep(2**server_errors)
                    server_errors += 1
                    continue
                elif 400 <= response.status <= 599:
                    raise fondat.error.errors[response.status](await response.text())
                else:
                    raise fondat.error.InternalServerError(
                        f"unexpected response: {response.status} {await response.text()}"
                    )
