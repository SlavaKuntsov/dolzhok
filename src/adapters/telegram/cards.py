"""Card rendering: Item -> compact HTML message (user content escaped)."""

from __future__ import annotations

import html
from typing import Any

from aiogram.enums import ParseMode

from src.adapters.telegram.keyboards import item_keyboard
from src.domain.entities import PIPELINE, Item, ItemStatus
from src.domain.value_objects import Money

STATUS_LABEL: dict[ItemStatus, str] = {
    ItemStatus.NEW: "новое",
    ItemStatus.ORDERED: "заказано",
    ItemStatus.RECEIVED: "получено",
    ItemStatus.CANCELLED: "отменено",
}


def _pipeline_line(item: Item) -> str:
    """One-line pipeline with the current step bold, e.g. 1 новое → 2 <b>заказано</b>."""
    if item.status == ItemStatus.CANCELLED:
        return "🚫 отменено"
    parts = []
    for number, status in enumerate(PIPELINE, start=1):
        name = STATUS_LABEL[status]
        if status == item.status:
            name = f"<b><u>{name}</u></b>"
        parts.append(f"{number} {name}")
    return " → ".join(parts)


def _money_line(item: Item) -> str:
    if item.price_kop is None:
        line = "💰 цены пока нет"
        return f"{line} · 🔢 ×{item.qty}" if item.qty > 1 else line
    price = Money(item.price_kop).format_rub()
    if item.qty > 1:
        return f"💰 {price} × {item.qty} = {Money(item.price_kop * item.qty).format_rub()}"
    return f"💰 {price}"


def format_item_card(item: Item) -> str:
    """Compact card: header with pipeline, optional title, money + link (HTML)."""
    lines = [f"#{item.id} · {_pipeline_line(item)}"]
    if item.title:
        lines.append(html.escape(item.title))
    lines.append(f"{_money_line(item)} · 🔗 {html.escape(item.url)}")
    return "\n".join(lines)


def card_message(item: Item, *, for_son: bool, prefix: str = "") -> dict[str, Any]:
    """Ready-to-splat kwargs for answer/send_message/edit_text with a card."""
    text = format_item_card(item)
    if prefix:
        text = f"{prefix}\n\n{text}"
    return {
        "text": text,
        "reply_markup": item_keyboard(item, for_son=for_son),
        "parse_mode": ParseMode.HTML,
        "disable_web_page_preview": True,
    }
