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


def test_debt_text_with_repayments() -> None:
    debt = CalcDebtResponse(debt_kop=259900, debt_count=1, postpaid_kop=0, postpaid_count=0)
    balance = CalcBalanceResponse(
        debt_kop=259900,
        debt_count=1,
        repaid_kop=100000,
        repaid_count=1,
        balance_kop=159900,
        advance_kop=0,
    )
    text = format_debt_text(debt, balance)
    assert "💰 Заказчик должен: 2 599,00 BYN (предоплата, 1 шт)" in text
    assert "💸 Погашено: 1 000,00 BYN (1 шт)" in text
    assert "✅ Остаток: 1 599,00 BYN" in text
    assert "Аванс" not in text


def test_debt_text_overpayment_shows_advance() -> None:
    debt = CalcDebtResponse(debt_kop=100000, debt_count=1, postpaid_kop=0, postpaid_count=0)
    balance = CalcBalanceResponse(
        debt_kop=100000,
        debt_count=1,
        repaid_kop=150000,
        repaid_count=1,
        balance_kop=-50000,
        advance_kop=50000,
    )
    text = format_debt_text(debt, balance)
    assert "✅ Остаток: 0,00 BYN" in text
    assert "🎁 Аванс: 500,00 BYN" in text
    assert "-500" not in text


def test_debt_text_keeps_postpaid_line() -> None:
    debt = CalcDebtResponse(debt_kop=0, debt_count=0, postpaid_kop=70000, postpaid_count=1)
    balance = CalcBalanceResponse(
        debt_kop=0, debt_count=0, repaid_kop=0, repaid_count=0, balance_kop=0, advance_kop=0
    )
    text = format_debt_text(debt, balance)
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
