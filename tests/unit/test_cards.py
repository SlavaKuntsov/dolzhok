"""Tests for compact HTML card rendering (Russian user-facing text)."""

from datetime import UTC, datetime

import pytest

from src.adapters.telegram.cards import format_item_card, item_summary
from src.domain.entities import Item, ItemStatus, PaymentType

FIXED = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def test_format_item_card_new_no_price() -> None:
    item = Item(id=1, url="https://ozon.by/t/abc", created_by=1, created_at=FIXED)
    assert format_item_card(item) == (
        "#1 · 1 <b><u>новое</u></b> → 2 заказано → 3 получено\n"
        "💰 цены пока нет\n"
        "🔗 https://ozon.by/t/abc · 📅 15.10.2026"
    )


def test_format_item_card_with_title_price_qty() -> None:
    item = Item(
        id=2,
        url="https://ozon.by/t/xyz",
        created_by=1,
        title="Втулка Д16мм",
        price_kop=129950,
        qty=2,
        status=ItemStatus.ORDERED,
        created_at=FIXED,
    )
    assert format_item_card(item) == (
        "#2 · 1 новое → 2 <b><u>заказано</u></b> → 3 получено\n"
        "Втулка Д16мм\n"
        "💰 1 299,50 BYN × 2 = 2 599,00 BYN · 💳 предоплата\n"
        "🔗 https://ozon.by/t/xyz · 📅 15.10.2026"
    )


def test_format_item_card_escapes_html() -> None:
    item = Item(
        id=3,
        url="https://ozon.ru/product/x?a=1&b=2",
        created_by=1,
        title="Втулка <16мм> & co",
    )
    card = format_item_card(item)
    assert "Втулка &lt;16мм&gt; &amp; co" in card
    assert "a=1&amp;b=2" in card
    assert "<16мм>" not in card


def test_format_item_card_qty_no_price() -> None:
    item = Item(id=5, url="https://ozon.ru/product/x-5", created_by=1, qty=3)
    card = format_item_card(item)
    assert "💰 цены пока нет · 🔢 ×3" in card


def test_format_item_card_cancelled() -> None:
    item = Item(id=7, url="https://ozon.ru/product/x-7", created_by=1, status=ItemStatus.CANCELLED)
    assert format_item_card(item).startswith("#7 · 🚫 отменено\n")


def test_format_item_card_prepaid_ordered() -> None:
    item = Item(
        id=8,
        url="https://ozon.ru/product/x-8",
        created_by=1,
        price_kop=129950,
        status=ItemStatus.ORDERED,
        payment=PaymentType.PREPAID,
    )
    assert "💰 1 299,50 BYN · 💳 предоплата" in format_item_card(item)


def test_format_item_card_returned() -> None:
    item = Item(
        id=9,
        url="https://ozon.ru/product/x-9",
        created_by=1,
        price_kop=129950,
        status=ItemStatus.CANCELLED,
        payment=PaymentType.PREPAID,
    )
    card = format_item_card(item)
    assert card.startswith("#9 · 🚫 отменено\n")
    assert "💰 1 299,50 BYN · ↩️ возврат" in card


def test_format_item_card_has_link_and_date() -> None:
    item = Item(id=10, url="https://ozon.ru/product/x-10", created_by=1, created_at=FIXED)
    card = format_item_card(item)
    assert "🔗 https://ozon.ru/product/x-10 · 📅 15.10.2026" in card


def test_item_summary_with_and_without_price() -> None:
    priced = Item(id=3, url="https://ozon.ru/product/x-3", created_by=1, price_kop=129950, qty=2)
    assert item_summary(priced) == "#3 · 🆕 · 2 599,00 BYN"
    unpriced = Item(id=4, url="https://ozon.ru/product/x-4", created_by=1)
    assert item_summary(unpriced) == "#4 · 🆕 · нет цены"


@pytest.mark.parametrize(
    ("title", "expected_segment"),
    [
        # canonical spec example: a Title under the cap passes through untouched
        ("Лента шлифовальная 760 мм, 25 мм P400", "Лента шлифовальная 760 мм, 25 мм P400"),
        # exactly 40 characters is untouched
        ("а" * 40, "а" * 40),
        # longer Title: cut at the last space at or before 40, head kept, ellipsis added
        (
            "Лента шлифовальная 760 мм, 25 мм P400 из Германии",
            "Лента шлифовальная 760 мм, 25 мм P400…",
        ),
        # last space sits exactly at index 39: keep characters 0..38, then `…`
        ("а" * 39 + " " + "б" * 10, "а" * 39 + "…"),
        # no space within the first 40 characters: hard-cut at 40 with ellipsis
        ("а" * 50, "а" * 40 + "…"),
        # newlines and runs of spaces collapse into single spaces
        ("Лента\nшлифовальная   760", "Лента шлифовальная 760"),
        # absent Title: no segment, no dangling separator
        (None, None),
        # whitespace-only Title is absent too
        ("   ", None),
        # `&`, `<` and quotes appear verbatim, never escaped
        ('Болт & гайка <M8> "x"', 'Болт & гайка <M8> "x"'),
    ],
)
def test_item_summary_title_segment(title: str | None, expected_segment: str | None) -> None:
    item = Item(id=1, url="https://ozon.ru/product/x-1", created_by=1, title=title)
    label = item_summary(item)
    if expected_segment is None:
        assert label == "#1 · 🆕 · нет цены"
    else:
        assert label == f"#1 · 🆕 · нет цены · {expected_segment}"


def test_item_summary_appends_title_after_formatted_money() -> None:
    """A priced Item carries its money and then the Title — not `нет цены`."""
    item = Item(
        id=1,
        url="https://ozon.ru/product/x-1",
        created_by=1,
        price_kop=2425,
        title="Дрель аккумуляторная",
    )
    assert item_summary(item) == "#1 · 🆕 · 24,25 BYN · Дрель аккумуляторная"
