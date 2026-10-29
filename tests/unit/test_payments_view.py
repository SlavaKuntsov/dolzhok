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
    debt_kop: int,
    *,
    debt_count: int = 1,
    manual_kop: int = 0,
    postpaid: int = 0,
    postpaid_count: int | None = None,
) -> CalcDebtResponse:
    return CalcDebtResponse(
        debt_kop=debt_kop,
        debt_count=debt_count,
        manual_kop=manual_kop,
        postpaid_kop=postpaid,
        postpaid_count=(postpaid_count if postpaid_count is not None else 1) if postpaid else 0,
    )


def _balance(
    debt_kop: int,
    *,
    debt_count: int = 1,
    manual_kop: int = 0,
    repaid_kop: int = 0,
    repaid_count: int = 0,
) -> CalcBalanceResponse:
    total = debt_kop + manual_kop
    balance = total - repaid_kop
    return CalcBalanceResponse(
        debt_kop=debt_kop,
        debt_count=debt_count,
        manual_kop=manual_kop,
        total_kop=total,
        repaid_kop=repaid_kop,
        repaid_count=repaid_count,
        balance_kop=balance,
        advance_kop=max(0, -balance),
    )


def test_debt_text_with_repayments() -> None:
    debt = _debt(259900)
    balance = _balance(259900, repaid_kop=100000, repaid_count=1)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "💰 Долг по товарам: 2 599,00 BYN (предоплата, 1 шт)" in text
    assert "📜 Долги за прошлое: 0,00 BYN" in text
    assert "🧾 Итого долг: 2 599,00 BYN" in text
    assert "💸 Погашено: 1 000,00 BYN (1 шт)" in text
    assert "✅ Остаток: 1 599,00 BYN" in text
    assert "Аванс" not in text


def test_debt_text_adds_manual_debt() -> None:
    debt = _debt(100000, manual_kop=50000)
    balance = _balance(100000, manual_kop=50000)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "📜 Долги за прошлое: 500,00 BYN" in text
    assert "🧾 Итого долг: 1 500,00 BYN" in text
    assert "✅ Остаток: 1 500,00 BYN" in text


def test_debt_text_negative_manual_debt() -> None:
    debt = _debt(100000, manual_kop=-30000)
    balance = _balance(100000, manual_kop=-30000)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "📜 Долги за прошлое: -300,00 BYN" in text
    assert "🧾 Итого долг: 700,00 BYN" in text


def test_debt_text_customer_sees_total_only() -> None:
    debt = _debt(100000, manual_kop=50000)
    balance = _balance(100000, manual_kop=50000, repaid_kop=20000, repaid_count=1)
    text = format_debt_text(debt, balance, for_executor=False)
    assert "💰 Долг: 1 500,00 BYN" in text
    assert "Долг по товарам" not in text
    assert "Долги за прошлое" not in text
    assert "✅ Остаток: 1 300,00 BYN" in text


def test_debt_text_overpayment_shows_advance() -> None:
    debt = _debt(100000)
    balance = _balance(100000, repaid_kop=150000, repaid_count=1)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "✅ Остаток: 0,00 BYN" in text
    assert "🎁 Аванс: 500,00 BYN" in text
    assert "-500" not in text


def test_debt_text_executor_layout_order() -> None:
    debt = _debt(50511, debt_count=5, postpaid=14284, postpaid_count=6)
    balance = _balance(50511, debt_count=5, repaid_kop=50000, repaid_count=2)
    text = format_debt_text(debt, balance, for_executor=True)
    assert text == (
        "💰 Долг по товарам: 505,11 BYN (предоплата, 5 шт)\n"
        "⏳ Ждет постоплаты: 142,84 BYN (6 шт)\n"
        "\n"
        "📜 Долги за прошлое: 0,00 BYN\n"
        "\n"
        "🧾 Итого долг: 505,11 BYN\n"
        "💸 Погашено: 500,00 BYN (2 шт)\n"
        "\n"
        "✅ Остаток: 5,11 BYN"
    )


def test_debt_text_executor_layout_with_advance() -> None:
    debt = _debt(72867, debt_count=6, postpaid=16231, postpaid_count=8)
    balance = _balance(72867, debt_count=6, repaid_kop=75000, repaid_count=3)
    text = format_debt_text(debt, balance, for_executor=True)
    assert text == (
        "💰 Долг по товарам: 728,67 BYN (предоплата, 6 шт)\n"
        "⏳ Ждет постоплаты: 162,31 BYN (8 шт)\n"
        "\n"
        "📜 Долги за прошлое: 0,00 BYN\n"
        "\n"
        "🧾 Итого долг: 728,67 BYN\n"
        "💸 Погашено: 750,00 BYN (3 шт)\n"
        "\n"
        "✅ Остаток: 0,00 BYN\n"
        "🎁 Аванс: 21,33 BYN"
    )


def test_debt_text_keeps_postpaid_line() -> None:
    debt = _debt(0, debt_count=0, postpaid=70000)
    balance = _balance(0, debt_count=0)
    text = format_debt_text(debt, balance, for_executor=True)
    assert "⏳ Ждет постоплаты: 700,00 BYN (1 шт)" in text
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
