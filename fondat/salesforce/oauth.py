"""Fondat Salesforce OAuth module."""

import aiohttp

from fondat.codec import JSONCodec
from fondat.data import datacls
from fondat.error import UnauthorizedError
from typing import Literal, Optional
from urllib.parse import urlencode


@datacls
class Token:
    access_token: str
    signature: str
    scope: Optional[str]
    instance_url: str
    id: str
    token_type: str
    issued_at: str
    refresh_token: Optional[str]
    state: Optional[str]


_token_codec = JSONCodec.get(Token)


def generate_authorization_url(
    *,
    endpoint: str,
    client_id: str,
    redirect_uri: str,
    scopes: Optional[list[str]] = None,
    state: Optional[str] = None,
    immediate: bool = False,
    display: Optional[Literal["page", "popup", "touch", "mobile"]] = None,
    login_hint: Optional[str] = None,
    nonce: Optional[str] = None,
    prompts: Optional[list[Literal["login", "consent", "select_account"]]] = None,
) -> str:
    """
    Generate a redirect URL to request an authorization code.

    Parameters:
    • endpoint: service endpoint, e.g. "https://login.salesforce.com"
    • client_id: connected app's consumer key
    • redirect_uri: URL where users are redirected after authorization
    • scopes: permissions that define type of protected resources to be accessed
    • state: state that external web service requests to be sent to the redirect URL
    • immediate: do not prompt user for login and approval
    • display: display type of the login and authorization pages
    • login_hint: username value to prepopulate in login page
    • nonce: used with "openid" scope to request token
    • prompts: how authorization server prompts for reauthentication and reapproval
    """

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes) if scopes is not None else None,
        "state": state,
        "immediate": "true" if immediate else None,
        "display": display,
        "login_hint": login_hint,
        "nonce": nonce,
        "prompt": " ".join(prompts) if prompts is not None else None,
    }

    return (
        endpoint.rstrip("/")
        + "/services/oauth2/authorize?"
        + urlencode({k: v for k, v in params.items() if v is not None})
    )


async def request_access_token(
    *,
    session: aiohttp.ClientSession,
    endpoint: str,
    client_id: str,
    client_secret: str,
    authorization_code: str,
    redirect_uri: str,
) -> Token:
    """
    Request an access token using the authorization code.

    Parameters:
    • session: client session to use for HTTP requests
    • endpoint: service endpoint, e.g. "https://login.salesforce.com"
    • client_id: connected app's consumer key
    • client_secret: connected app's consumer secret
    • authorization_code: temporary authorization code received from authorization server
    • redirect_uri: URL where users are redirected after authorization
    """

    async with await session.post(
        url=endpoint.rstrip("/") + "/services/oauth2/token",
        headers={"Accept": "application/json", "Accept-Encoding": "gzip"},
        data={
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        },
    ) as response:
        json = await response.json()
        if response.status == 200:
            return _token_codec.decode(json)
        raise UnauthorizedError(json["error"])


def password_authenticator(
    *,
    endpoint: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
):
    """
    Return an authentication coroutine that requests access token via username-password flow.

    Parameters:
    • endpoint: service endpoint, e.g. "https://login.salesforce.com"
    • client_id: connected app's consumer key
    • client_secret: connected app's consumer secret
    • username: username of user connected app is imitating
    • password: password of user connected app is imitating
    """

    async def authenticate(session: aiohttp.ClientSession) -> Token:
        async with await session.post(
            url=endpoint.rstrip("/") + "/services/oauth2/token",
            headers={"Accept": "application/json", "Accept-Encoding": "gzip"},
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


def refresh_authenticator(
    *,
    endpoint: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
):
    """
    Return an authentication coroutine that requests access token via refresh token flow.

    Parameters:
    • endpoint: service endpoint, e.g. "https://login.salesforce.com"
    • client_id: connected app's consumer key
    • client_secret: connected app's consumer secret
    • refresh_token: refresh token obtained via access token with refesh token scope
    """

    async def authenticate(session: aiohttp.ClientSession) -> Token:
        async with await session.post(
            url=endpoint.rstrip("/") + "/services/oauth2/token",
            headers={"Accept": "application/json", "Accept-Encoding": "gzip"},
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            },
        ) as response:
            json = await response.json()
            if response.status == 200:
                return _token_codec.decode(json)
            raise UnauthorizedError(json["error"])

    return authenticate
