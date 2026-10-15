"""Tests for keyboards: card actions and main menu."""

from src.adapters.telegram.keyboards import (
    BTN_CANCEL,
    BTN_DEBT,
    BTN_LIST,
    BTN_STATS,
    STATUS_BUTTON_LABEL,
    item_keyboard,
    main_menu_keyboard,
)
from src.domain.entities import Item, ItemStatus


def test_main_menu_has_all_actions() -> None:
    labels = [b.text for row in main_menu_keyboard().keyboard for b in row]
    assert labels == [BTN_LIST, BTN_DEBT, BTN_STATS, BTN_CANCEL]


def test_item_keyboard_shows_all_statuses_current_inert() -> None:
    item = Item(id=1, url="https://ozon.ru/product/x-1", created_by=1)
    keyboard = item_keyboard(item, for_son=True)
    assert keyboard is not None
    payloads = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert "noop:1" in payloads  # current NEW is shown but inert
    assert "st:1:ORDERED" in payloads
    assert "st:1:RECEIVED" in payloads
    assert "st:1:CANCELLED" in payloads
    assert "price:1" in payloads
    assert "qty:1" in payloads
    # Statuses live in their own rows, actions share the last row.
    assert len(keyboard.inline_keyboard) == 3
    last_row = [b.callback_data for b in keyboard.inline_keyboard[-1]]
    assert last_row == ["price:1", "qty:1"]


def test_received_card_has_reopen_button() -> None:
    item = Item(id=2, url="https://ozon.ru/product/x-2", created_by=1, status=ItemStatus.RECEIVED)
    keyboard = item_keyboard(item, for_son=True)
    assert keyboard is not None
    payloads = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert payloads == ["st:2:ORDERED"]


def test_item_keyboard_hidden_for_dad_and_cancelled() -> None:
    item = Item(id=1, url="https://ozon.ru/product/x-1", created_by=1)
    assert item_keyboard(item, for_son=False) is None
    cancelled = Item(
        id=2, url="https://ozon.ru/product/x-2", created_by=1, status=ItemStatus.CANCELLED
    )
    assert item_keyboard(cancelled, for_son=True) is None


def test_order_button_label() -> None:
    assert STATUS_BUTTON_LABEL[ItemStatus.ORDERED] == "2 📦 Заказан"
