"""Tests for compact card rendering (Russian user-facing text)."""

from src.adapters.telegram.cards import format_item_card
from src.domain.entities import Item, ItemStatus


def test_format_item_card_new_no_price() -> None:
    item = Item(id=1, url="https://ozon.by/t/abc", created_by=1)
    assert format_item_card(item) == (
        "#1 · 1 [новое] → 2 к заказу → 3 заказано → 4 получено\n"
        "💰 цены пока нет · 🔗 https://ozon.by/t/abc"
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
    )
    assert format_item_card(item) == (
        "#2 · 1 новое → 2 к заказу → 3 [заказано] → 4 получено\n"
        "Втулка Д16мм\n"
        "💰 1 299,50 ₽ × 2 = 2 599,00 ₽ · 🔗 https://ozon.by/t/xyz"
    )


def test_format_item_card_qty_no_price() -> None:
    item = Item(id=5, url="https://ozon.ru/product/x-5", created_by=1, qty=3)
    card = format_item_card(item)
    assert "💰 цены пока нет · 🔢 ×3" in card


def test_format_item_card_cancelled() -> None:
    item = Item(id=7, url="https://ozon.ru/product/x-7", created_by=1, status=ItemStatus.CANCELLED)
    assert format_item_card(item).startswith("#7 · 🚫 отменено\n")
