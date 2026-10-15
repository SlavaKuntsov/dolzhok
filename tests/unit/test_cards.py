"""Tests for compact HTML card rendering (Russian user-facing text)."""

from datetime import UTC, datetime

from src.adapters.telegram.cards import format_item_card, item_summary
from src.domain.entities import Item, ItemStatus, PaymentType

FIXED = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def test_format_item_card_new_no_price() -> None:
    item = Item(id=1, url="https://ozon.by/t/abc", created_by=1, created_at=FIXED)
    assert format_item_card(item) == (
        "#1 · 1 <b><u>новое</u></b> → 2 заказано → 3 получено\n"
        "💰 цены пока нет\n"
        "🔗 https://ozon.by/t/abc · 📅 15.10.2026"
    )


def test_format_item_card_with_title_price_qty() -> None:
    item = Item(
        id=2,
        url="https://ozon.by/t/xyz",
        created_by=1,
        title="Втулка Д16мм",
        price_kop=129950,
        qty=2,
        status=ItemStatus.ORDERED,
        created_at=FIXED,
    )
    assert format_item_card(item) == (
        "#2 · 1 новое → 2 <b><u>заказано</u></b> → 3 получено\n"
        "Втулка Д16мм\n"
        "💰 1 299,50 BYN × 2 = 2 599,00 BYN\n"
        "🔗 https://ozon.by/t/xyz · 📅 15.10.2026"
    )


def test_format_item_card_escapes_html() -> None:
    item = Item(
        id=3,
        url="https://ozon.ru/product/x?a=1&b=2",
        created_by=1,
        title="Втулка <16мм> & co",
    )
    card = format_item_card(item)
    assert "Втулка &lt;16мм&gt; &amp; co" in card
    assert "a=1&amp;b=2" in card
    assert "<16мм>" not in card


def test_format_item_card_qty_no_price() -> None:
    item = Item(id=5, url="https://ozon.ru/product/x-5", created_by=1, qty=3)
    card = format_item_card(item)
    assert "💰 цены пока нет · 🔢 ×3" in card


def test_format_item_card_cancelled() -> None:
    item = Item(id=7, url="https://ozon.ru/product/x-7", created_by=1, status=ItemStatus.CANCELLED)
    assert format_item_card(item).startswith("#7 · 🚫 отменено\n")


def test_format_item_card_prepaid_ordered() -> None:
    item = Item(
        id=8,
        url="https://ozon.ru/product/x-8",
        created_by=1,
        price_kop=129950,
        status=ItemStatus.ORDERED,
        payment=PaymentType.PREPAID,
    )
    assert "💰 1 299,50 BYN · 💳 предоплата" in format_item_card(item)


def test_format_item_card_returned() -> None:
    item = Item(
        id=9,
        url="https://ozon.ru/product/x-9",
        created_by=1,
        price_kop=129950,
        status=ItemStatus.CANCELLED,
        payment=PaymentType.PREPAID,
    )
    card = format_item_card(item)
    assert card.startswith("#9 · 🚫 отменено\n")
    assert "💰 1 299,50 BYN · ↩️ возврат" in card


def test_format_item_card_has_link_and_date() -> None:
    item = Item(id=10, url="https://ozon.ru/product/x-10", created_by=1, created_at=FIXED)
    card = format_item_card(item)
    assert "🔗 https://ozon.ru/product/x-10 · 📅 15.10.2026" in card


def test_item_summary_with_and_without_price() -> None:
    priced = Item(id=3, url="https://ozon.ru/product/x-3", created_by=1, price_kop=129950, qty=2)
    assert item_summary(priced) == "#3 · 🆕 · 2 599,00 BYN"
    unpriced = Item(id=4, url="https://ozon.ru/product/x-4", created_by=1)
    assert item_summary(unpriced) == "#4 · 🆕 · нет цены"
