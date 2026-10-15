"""Network adapter: resolve short ozo.ru links via HTTP redirects."""

from __future__ import annotations

import logging

import httpx

from src.domain.interfaces import IUrlResolver

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}


class HttpxOzonResolver(IUrlResolver):
    """Follow redirects (HEAD, then GET fallback); return input URL on failure."""

    def __init__(self, timeout: float = 5.0) -> None:
        self._timeout = timeout

    async def resolve(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=self._timeout, headers=_HEADERS
            ) as client:
                try:
                    response = await client.head(url)
                    if response.status_code < 400:
                        return str(response.url)
                except httpx.HTTPError:
                    pass
                async with client.stream("GET", url) as stream:
                    return str(stream.url)
        except httpx.HTTPError as exc:
            logger.warning("url resolve failed for %s (%s)", url, type(exc).__name__)
            return url
