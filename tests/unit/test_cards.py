"""Tests for card rendering (Russian user-facing text)."""

from src.adapters.telegram.cards import format_item_card, format_item_line
from src.domain.entities import Item, ItemStatus


def test_format_item_card_new_no_price() -> None:
    item = Item(id=1, url="https://ozon.ru/product/x-1", sku="123", created_by=1)
    card = format_item_card(item)
    assert "#1 🆕 новое" in card
    assert "https://ozon.ru/product/x-1" in card
    assert "цены пока нет" in card
    assert "Артикул 123" in card


def test_format_item_card_with_price() -> None:
    item = Item(
        id=2,
        url="https://ozon.ru/product/x-2",
        created_by=1,
        price_kop=129950,
        status=ItemStatus.ORDERED,
    )
    card = format_item_card(item)
    assert "#2 📦 заказано" in card
    assert "1 299,50 ₽" in card


def test_format_item_line() -> None:
    item = Item(id=3, url="https://ozon.ru/product/x-3", created_by=1, price_kop=50000)
    assert format_item_line(item) == "#3 🆕 500,00 ₽ https://ozon.ru/product/x-3"


def test_format_item_card_with_qty_and_price() -> None:
    item = Item(
        id=4, url="https://ozon.ru/product/x-4", created_by=1, price_kop=129950, qty=2
    )
    assert "1 299,50 ₽ × 2 = 2 599,00 ₽" in format_item_card(item)


def test_format_item_card_with_qty_no_price() -> None:
    item = Item(id=5, url="https://ozon.ru/product/x-5", created_by=1, qty=3)
    card = format_item_card(item)
    assert "🔢 Количество: 3" in card
