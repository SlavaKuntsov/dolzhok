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
from src.use_cases.calc_debt import CalcDebtResponse
from src.use_cases.list_repayments import ListRepaymentsResponse

_WHEN = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def _repayment(id_: int, amount: int, *, note: str | None = None, by: int = 9) -> Repayment:
    return Repayment(id=id_, amount_kop=amount, created_by=by, note=note, created_at=_WHEN)


def _debt(
    *,
    prepaid: int = 0,
    prepaid_count: int | None = None,
    postpaid: int = 0,
    postpaid_count: int | None = None,
    pending: int = 0,
    pending_count: int | None = None,
    manual_kop: int = 0,
) -> CalcDebtResponse:
    return CalcDebtResponse(
        debt_prepaid_kop=prepaid,
        debt_prepaid_count=prepaid_count if prepaid_count is not None else (1 if prepaid else 0),
        debt_postpaid_kop=postpaid,
        debt_postpaid_count=postpaid_count
        if postpaid_count is not None
        else (1 if postpaid else 0),
        pending_kop=pending,
        pending_count=pending_count if pending_count is not None else (1 if pending else 0),
        manual_kop=manual_kop,
    )


def _balance(
    *,
    prepaid: int = 0,
    prepaid_count: int | None = None,
    postpaid: int = 0,
    postpaid_count: int | None = None,
    manual_kop: int = 0,
    repaid_kop: int = 0,
) -> CalcBalanceResponse:
    prepaid_count = prepaid_count if prepaid_count is not None else (1 if prepaid else 0)
    postpaid_count = postpaid_count if postpaid_count is not None else (1 if postpaid else 0)
    total = prepaid + postpaid + manual_kop
    balance = total - repaid_kop
    return CalcBalanceResponse(
        debt_prepaid_kop=prepaid,
        debt_prepaid_count=prepaid_count,
        debt_postpaid_kop=postpaid,
        debt_postpaid_count=postpaid_count,
        manual_kop=manual_kop,
        total_kop=total,
        balance_kop=balance,
        advance_kop=max(0, -balance),
    )


def test_debt_text_executor_shows_split_and_remaining() -> None:
    """Executor sees what is already paid, split by payment type, plus the rest."""
    debt = _debt(
        prepaid=191527,
        prepaid_count=9,
        postpaid=58764,
        postpaid_count=19,
        pending=22278,
        pending_count=10,
    )
    balance = _balance(
        prepaid=191527,
        prepaid_count=9,
        postpaid=58764,
        postpaid_count=19,
        repaid_kop=190000,
    )
    text = format_debt_text(debt, balance, for_executor=True)
    assert text == (
        "💰 Уже оплачено за товары: 2 502,91 BYN\n"
        "  • предоплата: 1 915,27 BYN (9 шт)\n"
        "  • постоплата: 587,64 BYN (19 шт)\n"
        "\n"
        "📜 Долги за прошлое: 0,00 BYN\n"
        "\n"
        "⏳ Будет оплачено при получении: 222,78 BYN (10 шт)\n"
        "\n"
        "✅ Остаток: 602,91 BYN"
    )


def test_debt_text_drops_redundant_totals() -> None:
    """«Итого долг» (gross accrual) and «Погашено» are no longer shown."""
    debt = _debt(prepaid=259900)
    balance = _balance(prepaid=259900, repaid_kop=100000)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "Итого долг" not in text
    assert "Погашено" not in text
    assert "💰 Уже оплачено за товары: 2 599,00 BYN" in text
    assert "✅ Остаток: 1 599,00 BYN" in text
    assert "Аванс" not in text


def test_debt_text_omits_zero_bullets() -> None:
    """Nothing paid yet → no empty prepaid/postpaid bullets under the total."""
    debt = _debt()
    balance = _balance()
    text = format_debt_text(debt, balance, for_executor=True)
    assert "постоплата" not in text
    assert "предоплата" not in text
    assert "💰 Уже оплачено за товары: 0,00 BYN" in text


def test_debt_text_pending_is_not_in_remaining() -> None:
    """Pending postpaid is money not yet owed, so it stays out of the balance."""
    debt = _debt(prepaid=100000, pending=70000)
    balance = _balance(prepaid=100000)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "⏳ Будет оплачено при получении: 700,00 BYN (1 шт)" in text
    assert "✅ Остаток: 1 000,00 BYN" in text


def test_debt_text_adds_manual_debt() -> None:
    debt = _debt(prepaid=100000, manual_kop=50000)
    balance = _balance(prepaid=100000, manual_kop=50000)
    text = format_debt_text(debt, balance, for_executor=True)
    # The goods header stays the sum of its bullets; past-orders debt is its own line.
    assert "💰 Уже оплачено за товары: 1 000,00 BYN" in text
    assert "📜 Долги за прошлое: 500,00 BYN" in text
    assert "✅ Остаток: 1 500,00 BYN" in text


def test_debt_text_negative_manual_debt() -> None:
    debt = _debt(prepaid=100000, manual_kop=-30000)
    balance = _balance(prepaid=100000, manual_kop=-30000)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "📜 Долги за прошлое: -300,00 BYN" in text
    assert "✅ Остаток: 700,00 BYN" in text


def test_debt_text_customer_sees_total_only() -> None:
    debt = _debt(prepaid=100000, postpaid=50000, manual_kop=50000)
    balance = _balance(prepaid=100000, postpaid=50000, manual_kop=50000, repaid_kop=20000)
    text = format_debt_text(debt, balance, for_executor=False)
    assert "💰 Долг: 2 000,00 BYN" in text
    assert "предоплата" not in text
    assert "постоплата" not in text
    assert "Долги за прошлое" not in text
    assert "✅ Остаток: 1 800,00 BYN" in text


def test_debt_text_overpayment_shows_advance() -> None:
    debt = _debt(prepaid=100000)
    balance = _balance(prepaid=100000, repaid_kop=150000)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "✅ Остаток: 0,00 BYN" in text
    assert "🎁 Аванс: 500,00 BYN" in text
    assert "-500" not in text


def test_debt_text_executor_layout_with_advance() -> None:
    debt = _debt(prepaid=72867, prepaid_count=6, pending=16231, pending_count=8)
    balance = _balance(prepaid=72867, prepaid_count=6, repaid_kop=75000)
    text = format_debt_text(debt, balance, for_executor=True)
    assert text == (
        "💰 Уже оплачено за товары: 728,67 BYN\n"
        "  • предоплата: 728,67 BYN (6 шт)\n"
        "\n"
        "📜 Долги за прошлое: 0,00 BYN\n"
        "\n"
        "⏳ Будет оплачено при получении: 162,31 BYN (8 шт)\n"
        "\n"
        "✅ Остаток: 0,00 BYN\n"
        "🎁 Аванс: 21,33 BYN"
    )


def test_debt_text_pending_only_still_shows_pending() -> None:
    debt = _debt(pending=70000)
    balance = _balance()
    text = format_debt_text(debt, balance, for_executor=True)
    assert "⏳ Будет оплачено при получении: 700,00 BYN (1 шт)" in text
    assert "Остаток" not in text


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
