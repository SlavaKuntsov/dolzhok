"""Tests for list page rendering and keyboard (filters + pagination + view)."""

from src.adapters.telegram.keyboards import list_keyboard
from src.adapters.telegram.lists import list_page_message
from src.domain.entities import Item, ItemStatus
from src.use_cases.list_items import ListItemsResponse


def _item(
    item_id: int,
    status: ItemStatus = ItemStatus.NEW,
    price: int | None = None,
    title: str | None = None,
) -> Item:
    return Item(
        id=item_id,
        url=f"https://ozon.ru/product/x-{item_id}",
        created_by=1,
        status=status,
        price_kop=price,
        title=title,
    )


def _response(
    *,
    status: ItemStatus | None,
    page: int,
    pages: int,
    items: list[Item],
    total: int,
) -> ListItemsResponse:
    return ListItemsResponse(items=items, status=status, page=page, pages=pages, total=total)


def test_filter_row_marks_active_inert_and_others_switch() -> None:
    keyboard = list_keyboard(status=ItemStatus.NEW, page=0, pages=1, item_buttons=[])
    row = keyboard.inline_keyboard[0]
    payloads = [b.callback_data for b in row]
    assert payloads == [
        "lf:ALL",
        "nooplist:NEW",  # active filter is inert
        "lf:ORDERED",
        "lf:RECEIVED",
        "lf:CANCELLED",
    ]
    active = next(b for b in row if b.callback_data == "nooplist:NEW")
    assert active.text.startswith("▪️")


def test_item_buttons_open_cards() -> None:
    keyboard = list_keyboard(
        status=None,
        page=0,
        pages=1,
        item_buttons=[(7, "#7 · 🆕 · нет цены"), (6, "#6 · 📦 · 100,00 BYN")],
    )
    item_rows = keyboard.inline_keyboard[1:3]
    assert [b.callback_data for b in item_rows[0]] == ["view:7"]
    assert item_rows[1][0].text == "#6 · 📦 · 100,00 BYN"


def test_nav_arrows_inert_at_bounds() -> None:
    first = list_keyboard(status=None, page=0, pages=3, item_buttons=[])
    nav = first.inline_keyboard[-1]
    assert nav[0].callback_data == "nooplist:page"  # ← inert on first page
    assert nav[1].text == "1/3"
    assert nav[2].callback_data == "lp:ALL:1"

    last = list_keyboard(status=ItemStatus.ORDERED, page=2, pages=3, item_buttons=[])
    nav_last = last.inline_keyboard[-1]
    assert nav_last[0].callback_data == "lp:ORDERED:1"
    assert nav_last[2].callback_data == "nooplist:page"  # → inert on last page


def test_list_page_message_header_and_buttons() -> None:
    response = _response(
        status=None,
        page=1,
        pages=3,
        items=[_item(4, price=129950)],
        total=24,
    )
    kwargs = list_page_message(response)
    assert kwargs["text"] == "📋 Список · Все · стр. 2/3 · всего 24"
    buttons = kwargs["reply_markup"].inline_keyboard[1]
    assert buttons[0].callback_data == "view:4"


def test_list_page_message_empty_hint() -> None:
    response = _response(status=ItemStatus.RECEIVED, page=0, pages=1, items=[], total=0)
    kwargs = list_page_message(response)
    assert "стр. 1/1 · всего 0" in kwargs["text"]
    assert "Тут пока пусто." in kwargs["text"]
    # only filter row + nav row, no item rows
    assert len(kwargs["reply_markup"].inline_keyboard) == 2


def test_list_page_message_rows_show_titles() -> None:
    response = _response(
        status=None,
        page=0,
        pages=1,
        items=[
            _item(4, price=129950, title="Лента шлифовальная 760 мм, 25 мм P400"),
            _item(5, status=ItemStatus.ORDERED, title="Дрель аккумуляторная"),
        ],
        total=2,
    )
    kwargs = list_page_message(response)
    rows = kwargs["reply_markup"].inline_keyboard[1:3]
    assert rows[0][0].text == (
        "#4 · 🆕 · 1 299,50 BYN · Лента шлифовальная 760 мм, 25 мм P400"
    )
    assert rows[1][0].text == "#5 · 📦 · нет цены · Дрель аккумуляторная"
    # tapping a row still opens that Item's card
    assert rows[0][0].callback_data == "view:4"
    assert rows[1][0].callback_data == "view:5"


def test_list_page_message_untitled_item_keeps_short_label() -> None:
    response = _response(status=None, page=0, pages=1, items=[_item(6)], total=1)
    kwargs = list_page_message(response)
    label = kwargs["reply_markup"].inline_keyboard[1][0].text
    assert label == "#6 · 🆕 · нет цены"
