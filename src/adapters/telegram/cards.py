"""Card rendering: Item -> compact plain-text message (URLs stay raw)."""

from __future__ import annotations

from src.domain.entities import PIPELINE, Item, ItemStatus
from src.domain.value_objects import Money

STATUS_LABEL: dict[ItemStatus, str] = {
    ItemStatus.NEW: "новое",
    ItemStatus.TO_ORDER: "к заказу",
    ItemStatus.ORDERED: "заказано",
    ItemStatus.RECEIVED: "получено",
    ItemStatus.CANCELLED: "отменено",
}


def _pipeline_line(item: Item) -> str:
    """One-line pipeline with the current step in brackets, e.g. 1 новое → 2 [к заказу]."""
    if item.status == ItemStatus.CANCELLED:
        return "🚫 отменено"
    parts = []
    for number, status in enumerate(PIPELINE, start=1):
        name = STATUS_LABEL[status]
        if status == item.status:
            name = f"[{name}]"
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
    """Compact card: header with pipeline, optional title, money + link."""
    lines = [f"#{item.id} · {_pipeline_line(item)}"]
    if item.title:
        lines.append(item.title)
    lines.append(f"{_money_line(item)} · 🔗 {item.url}")
    return "\n".join(lines)
