"""Ozon URL normalization and SKU extraction. Pure, no network."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from src.domain.errors import DomainError

OZON_HOSTS = ("ozon.ru", "www.ozon.ru")
SHORT_HOSTS = ("ozo.ru", "www.ozo.ru")
KNOWN_HOSTS = OZON_HOSTS + SHORT_HOSTS

_URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
_SKU_RE = re.compile(r"-(\d{6,})/?$")


def extract_urls(text: str) -> list[str]:
    """Return all http(s) URLs found in the text."""
    return _URL_RE.findall(text)


def is_ozon_url(url: str) -> bool:
    """Check whether the URL belongs to Ozon (including short links)."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in KNOWN_HOSTS or host.endswith(".ozon.ru")


def is_short_url(url: str) -> bool:
    """Check whether the URL is a short ozo.ru link needing resolve."""
    host = (urlparse(url).hostname or "").lower()
    return host in SHORT_HOSTS


def normalize_url(url: str) -> str:
    """Normalize URL for dedup: lowercase host, drop query/fragment/trailing slash."""
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in KNOWN_HOSTS and not host.endswith(".ozon.ru"):
        raise DomainError(f"not an Ozon URL: {url!r}")
    if host == "www.ozon.ru":
        host = "ozon.ru"
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(("https", host, path, "", "", ""))


def extract_sku(normalized_url: str) -> str | None:
    """Best-effort SKU extraction from a normalized Ozon product URL."""
    match = _SKU_RE.search(normalized_url)
    return match.group(1) if match else None
