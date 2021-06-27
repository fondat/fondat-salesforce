"""Fondat Salesforce OAuth module."""

import aiohttp
import fondat.codec

from fondat.data import datacls
from fondat.error import UnauthorizedError


@datacls
class Token:
    access_token: str
    instance_url: str
    id: str
    token_type: str
    issued_at: str
    signature: str


_token_codec = fondat.codec.get_codec(fondat.codec.JSON, Token)


def password_authenticator(
    *,
    endpoint: str = "https://login.salesforce.com",
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
):
    async def authenticate(session: aiohttp.ClientSession) -> Token:
        async with await session.post(
            url=f"{endpoint}/services/oauth2/token",
            data={
                "grant_type": "password",
                "client_id": client_id,
                "client_secret": client_secret,
                "username": username,
                "password": password,
            },
        ) as response:
            json = await response.json()
            if response.status == 200:
                return _token_codec.decode(json)
            raise UnauthorizedError(json["error"])

    return authenticate
