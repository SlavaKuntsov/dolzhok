"""Inline keyboards for item cards. Son-only actions."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.domain.entities import Item, ItemStatus, allowed_next

STATUS_BUTTON_LABEL: dict[ItemStatus, str] = {
    ItemStatus.TO_ORDER: "📝 To order",
    ItemStatus.ORDERED: "📦 Ordered",
    ItemStatus.RECEIVED: "✅ Received",
    ItemStatus.CANCELLED: "🚫 Cancel",
}


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
    rows.append([InlineKeyboardButton(text="✏️ Price", callback_data=f"price:{item.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
