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


def test_normalize_non_ozon_raises() -> None:
    with pytest.raises(DomainError):
        ozon.normalize_url("https://example.com/x")


def test_extract_sku() -> None:
    assert ozon.extract_sku("https://ozon.ru/product/x-123456789") == "123456789"
    assert ozon.extract_sku("https://ozon.ru/category/phones") is None
