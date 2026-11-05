"""Tests for repayment/debt rendering (pure, no aiogram runtime)."""

from __future__ import annotations

from datetime import UTC, datetime

from src.adapters.telegram.payments import (
    format_debt_text,
    payments_message,
    repayment_confirm_message,
)
from src.domain.entities import Repayment
from src.use_cases.calc_balance import CalcBalanceResponse
from src.use_cases.calc_debt import CalcDebtResponse, MoneyCount
from src.use_cases.list_repayments import ListRepaymentsResponse

_WHEN = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def _repayment(id_: int, amount: int, *, note: str | None = None, by: int = 9) -> Repayment:
    return Repayment(id=id_, amount_kop=amount, created_by=by, note=note, created_at=_WHEN)


def _debt(
    *,
    prepaid_received: int = 0,
    prepaid_received_count: int | None = None,
    prepaid_ordered: int = 0,
    prepaid_ordered_count: int | None = None,
    postpaid_received: int = 0,
    postpaid_received_count: int | None = None,
    postpaid_ordered: int = 0,
    postpaid_ordered_count: int | None = None,
    manual_kop: int = 0,
    unpriced_count: int = 0,
) -> CalcDebtResponse:
    def mc(amount: int, count: int | None) -> MoneyCount:
        return MoneyCount(amount, count if count is not None else (1 if amount else 0))

    return CalcDebtResponse(
        prepaid_received=mc(prepaid_received, prepaid_received_count),
        prepaid_ordered=mc(prepaid_ordered, prepaid_ordered_count),
        postpaid_received=mc(postpaid_received, postpaid_received_count),
        postpaid_ordered=mc(postpaid_ordered, postpaid_ordered_count),
        manual_kop=manual_kop,
        unpriced_count=unpriced_count,
    )


def _balance(
    debt: CalcDebtResponse | None = None,
    *,
    repaid_kop: int = 0,
    repaid_count: int = 1 if False else 0,
) -> CalcBalanceResponse:
    return CalcBalanceResponse(
        debt=debt or _debt(),
        repaid_kop=repaid_kop,
        repaid_count=repaid_count if repaid_kop else 0,
    )


def test_debt_text_executor_explains_every_line() -> None:
    """Each quantity says what it is: paid-early (in hand vs in transit), on receipt."""
    debt = _debt(
        prepaid_received=72867,
        prepaid_received_count=6,
        prepaid_ordered=118660,
        prepaid_ordered_count=3,
        postpaid_received=58764,
        postpaid_received_count=19,
        postpaid_ordered=22278,
        postpaid_ordered_count=10,
    )
    text = format_debt_text(_balance(debt, repaid_kop=190000, repaid_count=4), for_executor=True)
    assert text == (
        "💰 Долг за товары: 2 502,91 BYN\n"
        "  • заплатил заранее: 1 915,27 BYN (9 шт: 6 уже у меня, 3 в пути)\n"
        "  • заплатил при получении: 587,64 BYN (19 шт)\n"
        "\n"
        "📜 Долги за прошлое: 0,00 BYN\n"
        "\n"
        "⏳ Ещё не долг, оплачу при получении: 222,78 BYN (10 шт)\n"
        "\n"
        "✅ Остаток: 602,91 BYN\n"
        "   долг 2 502,91 BYN − погашено 1 900,00 BYN"
    )


def test_debt_text_balance_shows_arithmetic() -> None:
    """The remaining line carries the subtraction that produced it."""
    debt = _debt(prepaid_received=100000)
    text = format_debt_text(_balance(debt, repaid_kop=40000, repaid_count=1), for_executor=True)
    assert "✅ Остаток: 600,00 BYN" in text
    assert "долг 1 000,00 BYN − погашено 400,00 BYN" in text


def test_debt_text_pending_is_not_in_remaining() -> None:
    """Pending postpaid is money not yet owed, so it stays out of the balance."""
    debt = _debt(prepaid_received=100000, postpaid_ordered=70000)
    text = format_debt_text(_balance(debt), for_executor=True)
    assert "⏳ Ещё не долг, оплачу при получении: 700,00 BYN (1 шт)" in text
    assert "✅ Остаток: 1 000,00 BYN" in text


def test_debt_text_flags_unpriced_work_items() -> None:
    """An in-work item with no price is announced, not silently dropped."""
    debt = _debt(prepaid_received=100000, unpriced_count=2)
    text = format_debt_text(_balance(debt), for_executor=True)
    assert "⚠️ Без цены: 2 шт — в долг не входят" in text


def test_debt_text_omits_zero_lines() -> None:
    """Nothing paid and nothing pending → no empty bullets or blocks."""
    text = format_debt_text(_balance(), for_executor=True)
    assert "заплатил заранее" not in text
    assert "заплатил при получении" not in text
    assert "оплачу при получении" not in text
    assert "💰 Долг за товары: 0,00 BYN" in text


def test_debt_text_adds_manual_debt() -> None:
    debt = _debt(prepaid_received=100000, manual_kop=50000)
    text = format_debt_text(_balance(debt), for_executor=True)
    # The goods header stays the sum of its bullets; past-orders debt is its own line.
    assert "💰 Долг за товары: 1 000,00 BYN" in text
    assert "📜 Долги за прошлое: 500,00 BYN" in text
    assert "✅ Остаток: 1 500,00 BYN" in text


def test_debt_text_negative_manual_debt() -> None:
    debt = _debt(prepaid_received=100000, manual_kop=-30000)
    text = format_debt_text(_balance(debt), for_executor=True)
    assert "📜 Долги за прошлое: -300,00 BYN" in text
    assert "✅ Остаток: 700,00 BYN" in text


def test_debt_text_customer_sees_total_only() -> None:
    debt = _debt(prepaid_received=100000, postpaid_received=50000, manual_kop=50000)
    text = format_debt_text(_balance(debt, repaid_kop=20000, repaid_count=1), for_executor=False)
    assert "💰 Долг: 2 000,00 BYN" in text
    assert "заплатил заранее" not in text
    assert "заплатил при получении" not in text
    assert "Долги за прошлое" not in text
    assert "✅ Остаток: 1 800,00 BYN" in text


def test_debt_text_overpayment_shows_advance() -> None:
    debt = _debt(prepaid_received=100000)
    text = format_debt_text(_balance(debt, repaid_kop=150000, repaid_count=1), for_executor=True)
    assert "✅ Остаток: 0,00 BYN" in text
    assert "🎁 Аванс: 500,00 BYN" in text
    assert "-500" not in text


def test_debt_text_executor_layout_with_advance() -> None:
    debt = _debt(
        prepaid_received=72867,
        prepaid_received_count=6,
        postpaid_ordered=16231,
        postpaid_ordered_count=8,
    )
    text = format_debt_text(_balance(debt, repaid_kop=75000, repaid_count=3), for_executor=True)
    assert text == (
        "💰 Долг за товары: 728,67 BYN\n"
        "  • заплатил заранее: 728,67 BYN (6 шт: 6 уже у меня)\n"
        "\n"
        "📜 Долги за прошлое: 0,00 BYN\n"
        "\n"
        "⏳ Ещё не долг, оплачу при получении: 162,31 BYN (8 шт)\n"
        "\n"
        "✅ Остаток: 0,00 BYN\n"
        "🎁 Аванс: 21,33 BYN\n"
        "   долг 728,67 BYN − погашено 750,00 BYN"
    )


def test_debt_text_pending_only_still_shows_pending() -> None:
    debt = _debt(postpaid_ordered=70000)
    text = format_debt_text(_balance(debt), for_executor=True)
    assert "⏳ Ещё не долг, оплачу при получении: 700,00 BYN (1 шт)" in text
    assert "Остаток" not in text


def test_debt_text_omits_zero_priced_pending_line() -> None:
    """A zero-priced pending item prints no line — zero sums stay out (story 8)."""
    debt = _debt(postpaid_ordered=0, postpaid_ordered_count=1)
    text = format_debt_text(_balance(debt), for_executor=True)
    assert "оплачу при получении" not in text


def _response(*repayments: Repayment) -> ListRepaymentsResponse:
    return ListRepaymentsResponse(
        repayments=list(repayments),
        total_kop=sum(r.amount_kop for r in repayments),
        count=len(repayments),
    )


def test_payments_message_renders_newest_first_with_details() -> None:
    response = _response(_repayment(2, 25000, note="второй"), _repayment(1, 100000, by=5))
    kwargs = payments_message(
        response, for_executor=True, author_names={9: "исполнитель", 5: "заказчик"}
    )
    text = kwargs["text"]
    assert "📜 Погашения · всего 2 · 1 250,00 BYN" in text
    assert "1. 15.10.2026 · 250,00 BYN · «второй» · исполнитель" in text
    assert "2. 15.10.2026 · 1 000,00 BYN · заказчик" in text
    callbacks = [b.callback_data for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert callbacks == ["delpay:2", "delpay:1"]


def test_payments_message_for_customer_has_no_buttons() -> None:
    kwargs = payments_message(
        _response(_repayment(1, 100000)), for_executor=False, author_names={9: "исполнитель"}
    )
    assert kwargs["reply_markup"] is None


def test_payments_message_empty() -> None:
    kwargs = payments_message(_response(), for_executor=True, author_names={9: "исполнитель"})
    assert "Пока пусто." in kwargs["text"]
    # Executor gets an empty inline keyboard so a prior message's buttons are cleared.
    assert kwargs["reply_markup"] is not None
    assert kwargs["reply_markup"].inline_keyboard == []


def test_payments_message_empty_for_customer_has_no_buttons() -> None:
    kwargs = payments_message(_response(), for_executor=False, author_names={9: "исполнитель"})
    assert kwargs["reply_markup"] is None


def test_payments_note_is_html_escaped() -> None:
    kwargs = payments_message(
        _response(_repayment(1, 100000, note="<b>x</b>")),
        for_executor=True,
        author_names={9: "исполнитель"},
    )
    assert "&lt;b&gt;x&lt;/b&gt;" in kwargs["text"]


def test_confirm_message_has_delete_and_cancel() -> None:
    kwargs = repayment_confirm_message(_repayment(3, 100000, note="заказ"), who="исполнитель")
    assert "🗑 Удалить погашение?" in kwargs["text"]
    callbacks = [b.callback_data for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert callbacks == ["delpayok:3", "delpayno:3"]
