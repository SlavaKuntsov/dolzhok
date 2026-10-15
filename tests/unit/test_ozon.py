"""Tests for Ozon URL helpers."""

import pytest

from src.domain import ozon
from src.domain.errors import DomainError


def test_extract_urls() -> None:
    text = "look https://www.ozon.ru/product/phone-123456789/ nice"
    assert ozon.extract_urls(text) == ["https://www.ozon.ru/product/phone-123456789/"]


@pytest.mark.parametrize(
    "url",
    [
        "https://www.ozon.ru/product/x-123456789/",
        "https://ozon.ru/product/x-123456789/",
        "https://m.ozon.ru/product/x-123456789/",
        "https://ozon.by/t/9oLOYk1",
        "https://www.ozon.by/product/x-123456789/",
        "https://ozon.kz/product/x-123456789/",
        "https://ozo.ru/abcDEF",
    ],
)
def test_is_ozon_url_true(url: str) -> None:
    assert ozon.is_ozon_url(url)


def test_is_ozon_url_false() -> None:
    assert not ozon.is_ozon_url("https://example.com/product-123/")


def test_normalize_url() -> None:
    assert (
        ozon.normalize_url("https://www.ozon.ru/product/x-123456789/?utm_source=tg#frag")
        == "https://ozon.ru/product/x-123456789"
    )
    assert ozon.normalize_url("https://m.ozon.ru/product/x-1/") == "https://ozon.ru/product/x-1"
    assert ozon.normalize_url("https://ozon.by/t/9oLOYk1") == "https://ozon.by/t/9oLOYk1"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://ozo.ru/abc", True),
        ("https://ozon.by/t/9oLOYk1", True),
        ("https://ozon.ru/t/abc", True),
        ("https://ozon.ru/product/x-123456789", False),
    ],
)
def test_is_short_url(url: str, expected: bool) -> None:
    assert ozon.is_short_url(url) is expected


def test_normalize_non_ozon_raises() -> None:
    with pytest.raises(DomainError):
        ozon.normalize_url("https://example.com/x")


def test_extract_sku() -> None:
    assert ozon.extract_sku("https://ozon.ru/product/x-123456789") == "123456789"
    assert ozon.extract_sku("https://ozon.ru/category/phones") is None


def test_extract_title() -> None:
    text = "Переходная втулка Д16мм https://ozon.by/t/9oLOYk1"
    assert ozon.extract_title(text, "https://ozon.by/t/9oLOYk1") == "Переходная втулка Д16мм"
    assert ozon.extract_title("https://ozon.ru/product/x-1", "https://ozon.ru/product/x-1") is None
