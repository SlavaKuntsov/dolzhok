"""Keyboards: inline actions on cards (son only) + main reply menu."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.domain.entities import Item, ItemStatus, allowed_next

STATUS_BUTTON_LABEL: dict[ItemStatus, str] = {
    ItemStatus.TO_ORDER: "📝 К заказу",
    ItemStatus.ORDERED: "📦 Заказан",
    ItemStatus.RECEIVED: "✅ Получен",
    ItemStatus.CANCELLED: "🚫 Отмена",
}

BTN_LIST = "📋 Список"
BTN_DEBT = "💰 Долг"
BTN_STATS = "📊 Статистика"
BTN_CANCEL = "❌ Отмена"


def item_keyboard(item: Item, *, for_son: bool) -> InlineKeyboardMarkup | None:
    """Build action keyboard. None for dad or closed items."""
    if not for_son or item.id is None or item.is_closed:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    status_row = [
        InlineKeyboardButton(
            text=STATUS_BUTTON_LABEL[target],
            callback_data=f"st:{item.id}:{target.value}",
        )
        for target in sorted(allowed_next(item.status), key=lambda s: s.value)
    ]
    if status_row:
        rows.append(status_row)
    rows.append([InlineKeyboardButton(text="✏️ Цена", callback_data=f"price:{item.id}")])
    rows.append([InlineKeyboardButton(text="🔢 Кол-во", callback_data=f"qty:{item.id}")])
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
