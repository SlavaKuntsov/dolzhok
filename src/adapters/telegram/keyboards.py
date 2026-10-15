"""Keyboards: inline actions on cards (son only) + main reply menu."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.domain.entities import PIPELINE, Item, ItemStatus

# Numbered in pipeline order; CANCELLED lives outside the pipeline.
STATUS_BUTTON_LABEL: dict[ItemStatus, str] = {
    ItemStatus.NEW: "1 🆕 Новое",
    ItemStatus.ORDERED: "2 📦 Заказан",
    ItemStatus.RECEIVED: "3 ✅ Получен",
    ItemStatus.CANCELLED: "🚫 Отмена",
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


def item_keyboard(item: Item, *, for_son: bool) -> InlineKeyboardMarkup | None:
    """Build action keyboard. None for dad or cancelled items.

    Layout: status rows (two per row, pipeline order), then Price + Qty.
    Received items get a single reopen button instead.
    """
    if not for_son or item.id is None or item.status == ItemStatus.CANCELLED:
        return None
    if item.status == ItemStatus.RECEIVED:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="↩️ В работу",
                        callback_data=f"st:{item.id}:{ItemStatus.ORDERED.value}",
                    )
                ]
            ]
        )
    all_statuses = [*PIPELINE, ItemStatus.CANCELLED]
    rows = [
        [_status_button(item.id, target, current=item.status) for target in row]
        for row in (all_statuses[i : i + 2] for i in range(0, len(all_statuses), 2))
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
