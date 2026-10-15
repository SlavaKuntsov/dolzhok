"""Tests for keyboards: card actions and main menu."""

from src.adapters.telegram.keyboards import (
    BTN_BACK,
    BTN_CANCEL,
    BTN_DEBT,
    BTN_DEBTS,
    BTN_LIST,
    BTN_PAY,
    BTN_PAYMENTS,
    BTN_STATS,
    STATUS_BUTTON_LABEL,
    debt_menu_keyboard,
    item_keyboard,
    main_menu_keyboard,
)
from src.domain.entities import Item, ItemStatus, PaymentType


def test_main_menu_has_all_actions() -> None:
    labels = [b.text for row in main_menu_keyboard().keyboard for b in row]
    assert labels == [BTN_LIST, BTN_DEBTS, BTN_STATS, BTN_CANCEL]


def test_debt_submenu_executor_has_pay() -> None:
    labels = [b.text for row in debt_menu_keyboard(for_executor=True).keyboard for b in row]
    assert labels == [BTN_DEBT, BTN_PAYMENTS, BTN_PAY, BTN_BACK]


def test_debt_submenu_customer_has_no_pay() -> None:
    labels = [b.text for row in debt_menu_keyboard(for_executor=False).keyboard for b in row]
    assert labels == [BTN_DEBT, BTN_PAYMENTS, BTN_BACK]
    assert BTN_PAY not in labels


def test_item_keyboard_shows_all_statuses_current_inert() -> None:
    item = Item(id=1, url="https://ozon.ru/product/x-1", created_by=1)
    keyboard = item_keyboard(item, for_executor=True)
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


def test_received_card_has_reopen_button_no_payment_toggle() -> None:
    item = Item(id=2, url="https://ozon.ru/product/x-2", created_by=1, status=ItemStatus.RECEIVED)
    keyboard = item_keyboard(item, for_executor=True)
    assert keyboard is not None
    payloads = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert payloads == ["st:2:ORDERED"]


def test_ordered_card_payment_toggle_offers_opposite() -> None:
    item = Item(
        id=3,
        url="https://ozon.ru/product/x-3",
        created_by=1,
        status=ItemStatus.ORDERED,
        payment=PaymentType.PREPAID,
    )
    keyboard = item_keyboard(item, for_executor=True)
    assert keyboard is not None
    payloads = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert "pay:3:POSTPAID" in payloads
    assert "pay:3:PREPAID" not in payloads
    labels = [b.text for row in keyboard.inline_keyboard for b in row]
    assert "💳 Сменить на постоплату" in labels


def test_postpaid_card_payment_toggle_offers_prepaid() -> None:
    item = Item(
        id=5,
        url="https://ozon.ru/product/x-5",
        created_by=1,
        status=ItemStatus.ORDERED,
        payment=PaymentType.POSTPAID,
    )
    keyboard = item_keyboard(item, for_executor=True)
    assert keyboard is not None
    payloads = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert "pay:5:PREPAID" in payloads
    assert "pay:5:POSTPAID" not in payloads


def test_new_card_has_no_payment_row() -> None:
    item = Item(id=4, url="https://ozon.ru/product/x-4", created_by=1)
    keyboard = item_keyboard(item, for_executor=True)
    assert keyboard is not None
    payloads = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert not any(str(p).startswith("pay:") for p in payloads)


def test_item_keyboard_hidden_for_customer() -> None:
    item = Item(id=1, url="https://ozon.ru/product/x-1", created_by=1)
    assert item_keyboard(item, for_executor=False) is None


def test_cancelled_card_has_reopen_button() -> None:
    cancelled = Item(
        id=2, url="https://ozon.ru/product/x-2", created_by=1, status=ItemStatus.CANCELLED
    )
    keyboard = item_keyboard(cancelled, for_executor=True)
    assert keyboard is not None
    payloads = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert payloads == ["st:2:ORDERED"]


def test_order_button_label() -> None:
    assert STATUS_BUTTON_LABEL[ItemStatus.ORDERED] == "2 📦 Заказан"
