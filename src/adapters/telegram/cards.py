"""Card rendering: Item -> compact HTML message (user content escaped)."""

from __future__ import annotations

import html
from typing import Any

from aiogram.enums import ParseMode

from src.adapters.telegram.keyboards import PAYMENT_STATUSES, item_keyboard
from src.domain.entities import PIPELINE, Item, ItemStatus, PaymentType
from src.domain.value_objects import Money

STATUS_LABEL: dict[ItemStatus, str] = {
    ItemStatus.NEW: "новое",
    ItemStatus.ORDERED: "заказано",
    ItemStatus.RECEIVED: "получено",
    ItemStatus.CANCELLED: "отменено",
}

PAYMENT_LABEL: dict[PaymentType, str] = {
    PaymentType.PREPAID: "💳 предоплата",
    PaymentType.POSTPAID: "💳 постоплата",
}

# Short status marker for compact list buttons.
STATUS_SHORT: dict[ItemStatus, str] = {
    ItemStatus.NEW: "🆕",
    ItemStatus.ORDERED: "📦",
    ItemStatus.RECEIVED: "✅",
    ItemStatus.CANCELLED: "🚫",
}


def _pipeline_line(item: Item) -> str:
    """One-line pipeline with the current step bold+underline."""
    if item.status == ItemStatus.CANCELLED:
        return "🚫 отменено"
    parts = []
    for number, status in enumerate(PIPELINE, start=1):
        name = STATUS_LABEL[status]
        if status == item.status:
            name = f"<b><u>{name}</u></b>"
        parts.append(f"{number} {name}")
    return " → ".join(parts)


def _payment_suffix(item: Item) -> str:
    if item.is_returned:
        return " · ↩️ возврат"
    if item.status in PAYMENT_STATUSES:
        return f" · {PAYMENT_LABEL[item.payment]}"
    return ""


def _money_line(item: Item) -> str:
    suffix = _payment_suffix(item)
    if item.price_kop is None:
        line = "💰 цены пока нет"
        return f"{line} · 🔢 ×{item.qty}{suffix}" if item.qty > 1 else f"{line}{suffix}"
    price = Money(item.price_kop).format_rub()
    if item.qty > 1:
        total = Money(item.price_kop * item.qty).format_rub()
        return f"💰 {price} × {item.qty} = {total}{suffix}"
    return f"💰 {price}{suffix}"


def _date_line(item: Item) -> str:
    return f"🔗 {html.escape(item.url)} · 📅 {item.created_at.strftime('%d.%m.%Y')}"


def format_item_card(item: Item) -> str:
    """Compact card: pipeline status, title, money, link + date (HTML)."""
    lines = [f"#{item.id} · {_pipeline_line(item)}"]
    if item.title:
        lines.append(html.escape(item.title))
    lines.append(_money_line(item))
    lines.append(_date_line(item))
    return "\n".join(lines)


# Compact list rows cut the Title to this many characters (Title segment only).
TITLE_MAX_LEN = 40


def _title_segment(title: str | None) -> str | None:
    """Single-line Title for a compact list row, or None when there is none.

    Whitespace runs (newlines included) collapse to one space. A normalized Title
    longer than TITLE_MAX_LEN is cut at the last space at or before the cap with
    `…` (keeping the identifying head); with no such space it hard-cuts at the
    cap. Not HTML-escaped: keyboard labels are plain text.
    """
    if not title:
        return None
    collapsed = " ".join(title.split())
    if not collapsed:
        return None
    if len(collapsed) <= TITLE_MAX_LEN:
        return collapsed
    head = collapsed[:TITLE_MAX_LEN]
    cut = head.rfind(" ")
    if cut == -1:
        return f"{head}…"
    return f"{head[:cut]}…"


def item_summary(item: Item) -> str:
    """One-line list entry: `#id · status · money · title` (no HTML)."""
    if item.total_kop is None:
        money = "нет цены"
    else:
        money = Money(item.total_kop).format_rub()
    label = f"#{item.id} · {STATUS_SHORT[item.status]} · {money}"
    title = _title_segment(item.title)
    if title is not None:
        label += f" · {title}"
    return label


def card_message(item: Item, *, for_executor: bool, prefix: str = "") -> dict[str, Any]:
    """Ready-to-splat kwargs for answer/send_message/edit_text with a card."""
    text = format_item_card(item)
    if prefix:
        text = f"{prefix}\n\n{text}"
    return {
        "text": text,
        "reply_markup": item_keyboard(item, for_executor=for_executor),
        "parse_mode": ParseMode.HTML,
        "disable_web_page_preview": True,
    }
