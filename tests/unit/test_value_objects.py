"""Tests for Money and price parsing."""

import pytest

from src.domain.errors import DomainError
from src.domain.value_objects import Money, parse_price_to_kop


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1299", 129900),
        ("1 299", 129900),
        ("1\u00a0299,50", 129950),
        ("1299.5", 129950),
        ("1299.99", 129999),
        ("0", 0),
        ("  250 ₽ ", 25000),
    ],
)
def test_parse_price_valid(text: str, expected: int) -> None:
    assert parse_price_to_kop(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "-50", "12,345", "1.2.3", ";;"])
def test_parse_price_invalid(text: str) -> None:
    with pytest.raises(DomainError):
        parse_price_to_kop(text)


def test_money_rejects_negative() -> None:
    with pytest.raises(DomainError):
        Money(-1)


def test_money_format_rub() -> None:
    assert Money(129950).format_rub() == "1 299,50 ₽"
