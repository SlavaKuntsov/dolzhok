"""Network adapter: resolve short ozo.ru links via HTTP redirects."""

from __future__ import annotations

import logging

import httpx

from src.domain.interfaces import IUrlResolver

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


class HttpxOzonResolver(IUrlResolver):
    """Follow redirects with HEAD; return input URL on any failure."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    async def resolve(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=self._timeout, headers=_HEADERS
            ) as client:
                response = await client.head(url)
                return str(response.url)
        except httpx.HTTPError as exc:
            logger.warning("url resolve failed for %s: %s", url, exc)
            return url
