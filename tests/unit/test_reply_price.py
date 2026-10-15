"""Tests for stateless price-by-reply parsing."""

from src.adapters.telegram.routers.items import parse_reply_price

CARD = "#2 🆕 новое\n\nВтулка\n\n🔗 https://ozon.by/t/9oLOYk1\n💰 цены пока нет"


def test_reply_price_ok() -> None:
    assert parse_reply_price("1 299,50", CARD) == (2, 129950)


def test_reply_price_no_card_id() -> None:
    assert parse_reply_price("100", "просто сообщение") is None
    assert parse_reply_price("100", None) is None


def test_reply_price_bad_amount() -> None:
    assert parse_reply_price("привет", CARD) is None
