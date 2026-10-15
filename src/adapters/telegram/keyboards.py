"""Keyboards: inline actions on cards (son only) + main reply menu."""

from __future__ import annotations

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

PAYMENT_BUTTON_LABEL: dict[PaymentType, str] = {
    PaymentType.PREPAID: "💳 Предоплата",
    PaymentType.POSTPAID: "💳 Постоплата",
}

BTN_LIST = "📋 Список"
BTN_DEBT = "💰 Долг"
BTN_STATS = "📊 Статистика"
BTN_CANCEL = "❌ Отмена"


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


def _payment_row(item_id: int, *, current: PaymentType | None) -> list[InlineKeyboardButton]:
    """Prepaid/Postpaid buttons; the current choice is inert (noop)."""
    row = []
    for payment in (PaymentType.PREPAID, PaymentType.POSTPAID):
        if payment is current:
            row.append(
                InlineKeyboardButton(
                    text=f"▪️ {PAYMENT_BUTTON_LABEL[payment]}",
                    callback_data=f"nooppay:{item_id}",
                )
            )
        else:
            row.append(
                InlineKeyboardButton(
                    text=PAYMENT_BUTTON_LABEL[payment],
                    callback_data=f"pay:{item_id}:{payment.value}",
                )
            )
    return row


def item_keyboard(item: Item, *, for_son: bool) -> InlineKeyboardMarkup | None:
    """Build action keyboard. None for dad or cancelled items.

    Layout: status rows (two per row, pipeline order), then Price + Qty, then a
    payment row for ordered/received items. Received items get a reopen button.
    """
    if not for_son or item.id is None or item.status == ItemStatus.CANCELLED:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    if item.status == ItemStatus.RECEIVED:
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
    if item.status in PAYMENT_STATUSES:
        rows.append(_payment_row(item.id, current=item.payment))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply menu with all global actions."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LIST), KeyboardButton(text=BTN_DEBT)],
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
