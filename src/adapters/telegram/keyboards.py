"""Keyboards: inline actions on cards (son only) + main reply menu."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.domain.entities import Item, ItemStatus

STATUS_BUTTON_LABEL: dict[ItemStatus, str] = {
    ItemStatus.NEW: "🆕 Новое",
    ItemStatus.TO_ORDER: "📝 Заказать",
    ItemStatus.ORDERED: "📦 Заказан",
    ItemStatus.RECEIVED: "✅ Получен",
    ItemStatus.CANCELLED: "🚫 Отмена",
}

BTN_LIST = "📋 Список"
BTN_DEBT = "💰 Долг"
BTN_STATS = "📊 Статистика"
BTN_CANCEL = "❌ Отмена"


def _chunked_statuses(current: ItemStatus) -> list[list[ItemStatus]]:
    """All other pipeline statuses, two buttons per row."""
    others = sorted((s for s in ItemStatus if s != current), key=lambda s: s.value)
    return [others[i : i + 2] for i in range(0, len(others), 2)]


def item_keyboard(item: Item, *, for_son: bool) -> InlineKeyboardMarkup | None:
    """Build action keyboard. None for dad or closed items.

    Layout: separate row(s) of status buttons, then one row with Price + Qty.
    """
    if not for_son or item.id is None or item.is_closed:
        return None
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=STATUS_BUTTON_LABEL[target],
                callback_data=f"st:{item.id}:{target.value}",
            )
            for target in row
        ]
        for row in _chunked_statuses(item.status)
    ]
    rows.append(
        [
            InlineKeyboardButton(text="✏️ Цена", callback_data=f"price:{item.id}"),
            InlineKeyboardButton(text="🔢 Кол-во", callback_data=f"qty:{item.id}"),
        ]
    )
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
