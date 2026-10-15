"""List page rendering: ListItemsResponse -> one message with filters + paging."""

from __future__ import annotations

from typing import Any

from src.adapters.telegram.cards import item_summary
from src.adapters.telegram.keyboards import LIST_FILTER_LABEL, list_keyboard
from src.use_cases.list_items import ListItemsResponse


def list_page_message(response: ListItemsResponse) -> dict[str, Any]:
    """Ready-to-splat kwargs for answer/edit_text showing one list page."""
    filter_key = response.status.value if response.status is not None else "ALL"
    filter_label = LIST_FILTER_LABEL[filter_key]
    header = (
        f"📋 Список · {filter_label} · стр. {response.page + 1}/{response.pages} "
        f"· всего {response.total}"
    )
    if not response.items:
        header += "\n\nТут пока пусто."
    item_buttons = [(item.id, item_summary(item)) for item in response.items if item.id is not None]
    return {
        "text": header,
        "reply_markup": list_keyboard(
            status=response.status,
            page=response.page,
            pages=response.pages,
            item_buttons=item_buttons,
        ),
        "disable_web_page_preview": True,
    }
