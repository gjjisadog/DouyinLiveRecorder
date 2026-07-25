# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from typing import Any, AsyncIterator, Dict, Iterator

import httpx

from .. import utils

OptionalStr = str | None
OptionalDict = Dict[str, Any] | None
_shared_client: ContextVar[httpx.AsyncClient | None] = ContextVar("dlr_async_http_client", default=None)


def get_shared_client() -> httpx.AsyncClient | None:
    """Return the daemon-scoped client inherited by the current asyncio task."""
    return _shared_client.get()


@contextmanager
def use_async_client(client: httpx.AsyncClient) -> Iterator[None]:
    """Make one pooled client available to all parser calls in this context."""
    token: Token = _shared_client.set(client)
    try:
        yield
    finally:
        _shared_client.reset(token)


@asynccontextmanager
async def request_client(
        proxy_addr: OptionalStr = None,
        timeout: int = 20,
        verify: bool = True,
        http2: bool = True
) -> AsyncIterator[httpx.AsyncClient]:
    """Use the daemon client when present, retaining a legacy standalone fallback."""
    client = get_shared_client()
    if client is not None:
        yield client
        return

    proxy_addr = utils.handle_proxy_addr(proxy_addr)
    async with httpx.AsyncClient(
            proxy=proxy_addr,
            timeout=timeout,
            verify=verify,
            http2=http2,
            follow_redirects=True
    ) as temporary_client:
        yield temporary_client


async def async_req(
        url: str,
        proxy_addr: OptionalStr = None,
        headers: OptionalDict = None,
        data: dict | bytes | None = None,
        json_data: dict | list | None = None,
        timeout: int = 20,
        redirect_url: bool = False,
        return_cookies: bool = False,
        include_cookies: bool = False,
        abroad: bool = False,
        content_conding: str = 'utf-8',
        verify: bool = True,
        http2: bool = True
) -> OptionalDict | OptionalStr | tuple:
    if headers is None:
        headers = {}
    try:
        async with request_client(proxy_addr, timeout, verify, http2) as client:
            if data or json_data:
                response = await client.post(
                    url,
                    data=data,
                    json=json_data,
                    headers=headers,
                    timeout=timeout,
                )
            else:
                response = await client.get(
                    url,
                    headers=headers,
                    follow_redirects=True,
                    timeout=timeout,
                )

        if redirect_url:
            return str(response.url)
        elif return_cookies:
            cookies_dict = {name: value for name, value in response.cookies.items()}
            return (response.text, cookies_dict) if include_cookies else cookies_dict
        else:
            resp_str = response.text
    except Exception as e:
        resp_str = str(e)

    return resp_str


async def get_response_status(url: str, proxy_addr: OptionalStr = None, headers: OptionalDict = None,
                              timeout: int = 10, abroad: bool = False, verify: bool = True, http2=False) -> bool:

    try:
        async with request_client(proxy_addr, timeout, verify, http2) as client:
            response = await client.head(
                url,
                headers=headers,
                follow_redirects=True,
                timeout=timeout,
            )
            return response.status_code == 200
    except Exception as e:
        print(e)
    return False
