"""Tests for keyboards: card actions and main menu."""

from src.adapters.telegram.keyboards import (
    BTN_CANCEL,
    BTN_DEBT,
    BTN_LIST,
    BTN_STATS,
    item_keyboard,
    main_menu_keyboard,
)
from src.domain.entities import Item, ItemStatus


def test_main_menu_has_all_actions() -> None:
    labels = [b.text for row in main_menu_keyboard().keyboard for b in row]
    assert labels == [BTN_LIST, BTN_DEBT, BTN_STATS, BTN_CANCEL]


def test_item_keyboard_new_has_transitions_and_price() -> None:
    item = Item(id=1, url="https://ozon.ru/product/x-1", created_by=1)
    keyboard = item_keyboard(item, for_son=True)
    assert keyboard is not None
    payloads = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert "st:1:TO_ORDER" in payloads
    assert "st:1:CANCELLED" in payloads
    assert "price:1" in payloads
    assert "qty:1" in payloads


def test_item_keyboard_hidden_for_dad_and_closed() -> None:
    item = Item(id=1, url="https://ozon.ru/product/x-1", created_by=1)
    assert item_keyboard(item, for_son=False) is None
    closed = Item(id=2, url="https://ozon.ru/product/x-2", created_by=1, status=ItemStatus.RECEIVED)
    assert item_keyboard(closed, for_son=True) is None
