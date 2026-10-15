"""Card rendering: Item -> plain-text message (no parse_mode, URLs stay raw)."""

from __future__ import annotations

from src.domain.entities import Item, ItemStatus
from src.domain.value_objects import Money

STATUS_EMOJI: dict[ItemStatus, str] = {
    ItemStatus.NEW: "🆕",
    ItemStatus.TO_ORDER: "📝",
    ItemStatus.ORDERED: "📦",
    ItemStatus.RECEIVED: "✅",
    ItemStatus.CANCELLED: "🚫",
}

STATUS_LABEL: dict[ItemStatus, str] = {
    ItemStatus.NEW: "new",
    ItemStatus.TO_ORDER: "to order",
    ItemStatus.ORDERED: "ordered",
    ItemStatus.RECEIVED: "received",
    ItemStatus.CANCELLED: "cancelled",
}


def format_item_card(item: Item) -> str:
    """Full card for a single item message."""
    emoji = STATUS_EMOJI[item.status]
    label = STATUS_LABEL[item.status]
    price = Money(item.price_kop).format_rub() if item.price_kop is not None else "no price yet"
    lines = [f"#{item.id} {emoji} {label}", "", f"🔗 {item.url}", f"💰 {price}"]
    if item.sku:
        lines.append(f"🏷 SKU {item.sku}")
    return "\n".join(lines)


def format_item_line(item: Item) -> str:
    """Compact one-liner for /list output."""
    emoji = STATUS_EMOJI[item.status]
    price = Money(item.price_kop).format_rub() if item.price_kop is not None else "—"
    return f"#{item.id} {emoji} {price} {item.url}"
