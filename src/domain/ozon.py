"""Ozon URL normalization and SKU extraction. Pure, no network."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from src.domain.errors import DomainError

# Ozon storefronts: ru/by/kz/com/uz + short ozo.ru. www./m. prefixes are stripped.
_HOST_RE = re.compile(r"^(?:www\.|m\.)?(ozon\.(?:ru|by|kz|com|uz)|ozo\.ru)$", re.IGNORECASE)
_SHORT_HOST = "ozo.ru"

_URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
_SKU_RE = re.compile(r"-(\d{6,})/?$")


def extract_urls(text: str) -> list[str]:
    """Return all http(s) URLs found in the text."""
    return _URL_RE.findall(text)


def _canonical_host(url: str) -> str | None:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return None
    match = _HOST_RE.match(host)
    return match.group(1).lower() if match else None


def is_ozon_url(url: str) -> bool:
    """Check whether the URL belongs to Ozon (any locale, incl. short links)."""
    return _canonical_host(url) is not None


def is_short_url(url: str) -> bool:
    """Check whether the URL needs HTTP resolve (ozo.ru or /t/ share links)."""
    host = _canonical_host(url)
    if host is None:
        return False
    if host == _SHORT_HOST:
        return True
    return urlparse(url).path.startswith("/t/")


def normalize_url(url: str) -> str:
    """Normalize URL for dedup: canonical host, drop query/fragment/trailing slash."""
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    host = _canonical_host(url)
    if host is None:
        raise DomainError(f"not an Ozon URL: {url!r}")
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(("https", host, path, "", "", ""))


def extract_sku(normalized_url: str) -> str | None:
    """Best-effort SKU extraction from a normalized Ozon product URL."""
    match = _SKU_RE.search(normalized_url)
    return match.group(1) if match else None


def extract_title(text: str, url: str) -> str | None:
    """Take message text before the URL as item title (user-typed product name)."""
    head = text.split(url, 1)[0].strip()
    if not head:
        return None
    return head[:200]
