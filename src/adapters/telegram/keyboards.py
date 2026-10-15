"""Keyboards: inline actions on cards (executor only) + main reply menu."""

from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.domain.entities import PIPELINE, Item, ItemStatus, PaymentType

# Numbered in pipeline order; CANCELLED lives outside the pipeline.
STATUS_BUTTON_LABEL: dict[ItemStatus, str] = {
    ItemStatus.NEW: "1 🆕 Новое",
    ItemStatus.ORDERED: "2 📦 Заказан",
    ItemStatus.RECEIVED: "3 ✅ Получен",
    ItemStatus.CANCELLED: "🚫 Отмена",
}

# Payment only matters once an item is ordered or received.
PAYMENT_STATUSES: frozenset[ItemStatus] = frozenset({ItemStatus.ORDERED, ItemStatus.RECEIVED})

# Single toggle button: label is the method it switches TO.
PAYMENT_TOGGLE_LABEL: dict[PaymentType, str] = {
    PaymentType.PREPAID: "💳 Сменить на предоплату",
    PaymentType.POSTPAID: "💳 Сменить на постоплату",
}

BTN_LIST = "📋 Список"
BTN_DEBTS = "💰 Долги"
BTN_STATS = "📊 Статистика"
BTN_CANCEL = "❌ Отмена"
# Inside the "💰 Долги" submenu; BTN_DEBTS above only opens it.
BTN_DEBT = "💰 Долг"
BTN_PAY = "💸 Погасить"
BTN_PAYMENTS = "📜 Погашения"
BTN_BACK = "⬅️ Назад"

# List filter buttons: "ALL" plus one per status. Active filter is inert.
LIST_FILTER_LABEL: dict[str, str] = {
    "ALL": "Все",
    ItemStatus.NEW.value: "🆕",
    ItemStatus.ORDERED.value: "📦",
    ItemStatus.RECEIVED.value: "✅",
    ItemStatus.CANCELLED.value: "🚫",
}


def _status_button(
    item_id: int, target: ItemStatus, *, current: ItemStatus
) -> InlineKeyboardButton:
    """All statuses stay visible; the current one is inert (noop)."""
    if target == current:
        return InlineKeyboardButton(
            text=f"▪️ {STATUS_BUTTON_LABEL[target]}",
            callback_data=f"noop:{item_id}",
        )
    return InlineKeyboardButton(
        text=STATUS_BUTTON_LABEL[target],
        callback_data=f"st:{item_id}:{target.value}",
    )


def _payment_button(item_id: int, *, current: PaymentType) -> InlineKeyboardButton:
    """One toggle button that switches to the opposite payment method.

    The card already prints the current method (💳 предоплата/постоплата), so the
    button only offers the other one.
    """
    target = PaymentType.POSTPAID if current is PaymentType.PREPAID else PaymentType.PREPAID
    return InlineKeyboardButton(
        text=PAYMENT_TOGGLE_LABEL[target],
        callback_data=f"pay:{item_id}:{target.value}",
    )


def item_keyboard(item: Item, *, for_executor: bool) -> InlineKeyboardMarkup | None:
    """Build action keyboard. None for customer.

    Layout: for open items — status rows (two per row, pipeline order) then Price
    + Qty; for closed items (received/cancelled) — a single reopen button back to
    `ORDERED`. Only `ORDERED` items get the payment toggle row (receiving settles
    the order, so payment is shown but no longer switchable).
    """
    if not for_executor or item.id is None:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    if item.is_closed:
        rows.append(
            [
                InlineKeyboardButton(
                    text="↩️ В работу",
                    callback_data=f"st:{item.id}:{ItemStatus.ORDERED.value}",
                )
            ]
        )
    else:
        all_statuses = [*PIPELINE, ItemStatus.CANCELLED]
        rows += [
            [_status_button(item.id, target, current=item.status) for target in row]
            for row in (all_statuses[i : i + 2] for i in range(0, len(all_statuses), 2))
        ]
        rows.append(
            [
                InlineKeyboardButton(text="✏️ Цена", callback_data=f"price:{item.id}"),
                InlineKeyboardButton(text="🔢 Кол-во", callback_data=f"qty:{item.id}"),
            ]
        )
    if item.status is ItemStatus.ORDERED:
        rows.append([_payment_button(item.id, current=item.payment)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def list_keyboard(
    *,
    status: ItemStatus | None,
    page: int,
    pages: int,
    item_buttons: Sequence[tuple[int, str]],
) -> InlineKeyboardMarkup:
    """Inline keyboard for one list page: filters, items, prev/next.

    `item_buttons` are `(item_id, label)` pairs; tapping runs `view:<id>`.
    The active filter and out-of-range arrows are inert (`nooplist:`).
    """
    current = status.value if status is not None else "ALL"
    filter_row = [
        InlineKeyboardButton(
            text=f"▪️ {label}" if value == current else label,
            callback_data=f"nooplist:{value}" if value == current else f"lf:{value}",
        )
        for value, label in LIST_FILTER_LABEL.items()
    ]
    rows: list[list[InlineKeyboardButton]] = [filter_row]
    rows += [
        [InlineKeyboardButton(text=label, callback_data=f"view:{item_id}")]
        for item_id, label in item_buttons
    ]
    prev_page = (
        InlineKeyboardButton(text="◀️", callback_data=f"lp:{current}:{page - 1}")
        if page > 0
        else InlineKeyboardButton(text="◀️", callback_data="nooplist:page")
    )
    next_page = (
        InlineKeyboardButton(text="▶️", callback_data=f"lp:{current}:{page + 1}")
        if page < pages - 1
        else InlineKeyboardButton(text="▶️", callback_data="nooplist:page")
    )
    rows.append(
        [
            prev_page,
            InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="nooplist:page"),
            next_page,
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply menu; money actions live under the «💰 Долги» submenu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LIST), KeyboardButton(text=BTN_DEBTS)],
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def debt_menu_keyboard(*, for_executor: bool) -> ReplyKeyboardMarkup:
    """Submenu for debt/repayments.

    Executor gets the «💸 Погасить» entry; customer sees the read-only actions only.
    """
    rows = [[KeyboardButton(text=BTN_DEBT), KeyboardButton(text=BTN_PAYMENTS)]]
    if for_executor:
        rows.append([KeyboardButton(text=BTN_PAY), KeyboardButton(text=BTN_BACK)])
    else:
        rows.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
    )
