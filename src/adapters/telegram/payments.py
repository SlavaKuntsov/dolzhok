"""Repayment views: debt balance text, ledger list, delete confirmation."""

from __future__ import annotations

import html
from collections.abc import Mapping
from typing import Any

from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.domain.entities import Repayment
from src.domain.value_objects import Money
from src.use_cases.calc_balance import CalcBalanceResponse
from src.use_cases.calc_debt import CalcDebtResponse
from src.use_cases.list_repayments import ListRepaymentsResponse


def _money(kop: int) -> str:
    return Money(kop).format_rub()


def format_debt_text(debt: CalcDebtResponse, balance: CalcBalanceResponse) -> str:
    """Debt summary: owed, repaid, remaining balance (or advance), postpaid."""
    lines = [f"💰 Папа должен: {_money(balance.debt_kop)} (предоплата, {balance.debt_count} шт)"]
    if balance.repaid_count:
        lines.append(f"💸 Погашено: {_money(balance.repaid_kop)} ({balance.repaid_count} шт)")
    if balance.advance_kop:
        lines.append("✅ Остаток: 0,00 BYN")
        lines.append(f"🎁 Аванс: {_money(balance.advance_kop)}")
    elif balance.debt_count or balance.repaid_count:
        lines.append(f"✅ Остаток: {_money(balance.balance_kop)}")
    if debt.postpaid_count:
        lines.append(f"⏳ Ждет постоплаты: {_money(debt.postpaid_kop)} ({debt.postpaid_count} шт)")
    return "\n".join(lines)


def _repayment_line(index: int, repayment: Repayment, who: str) -> str:
    date = repayment.created_at.strftime("%d.%m.%Y")
    parts = [f"{index}. {date} · {_money(repayment.amount_kop)}"]
    if repayment.note:
        parts.append(f"«{html.escape(repayment.note)}»")
    parts.append(who)
    return " · ".join(parts)


def payments_message(
    response: ListRepaymentsResponse,
    *,
    for_son: bool,
    author_names: Mapping[int, str],
) -> dict[str, Any]:
    """Ready-to-splat kwargs for the ledger list; son gets a 🗑 per entry.

    Son always receives an inline keyboard (possibly empty) so that re-rendering
    over a message with delete buttons actually clears them — Telegram keeps the
    old markup when ``reply_markup`` is omitted.
    """
    keyboard: InlineKeyboardMarkup | None = None
    if for_son:
        rows = [
            [InlineKeyboardButton(text=f"🗑 {_money(r.amount_kop)}", callback_data=f"delpay:{r.id}")]
            for r in response.repayments
            if r.id is not None
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    lines = [f"📜 Погашения · всего {response.count} · {_money(response.total_kop)}"]
    if not response.repayments:
        lines += ["", "Пока пусто."]
    else:
        lines.append("")
        for index, repayment in enumerate(response.repayments, start=1):
            lines.append(
                _repayment_line(index, repayment, author_names.get(repayment.created_by, "—"))
            )

    return {
        "text": "\n".join(lines),
        "reply_markup": keyboard,
        "parse_mode": ParseMode.HTML,
        "disable_web_page_preview": True,
    }


def repayment_confirm_message(repayment: Repayment, *, who: str) -> dict[str, Any]:
    """Ready-to-splat kwargs asking son to confirm deletion of one entry."""
    date = repayment.created_at.strftime("%d.%m.%Y")
    line = f"{date} · {_money(repayment.amount_kop)} · {who}"
    if repayment.note:
        line += f" · «{html.escape(repayment.note)}»"
    return {
        "text": f"🗑 Удалить погашение?\n{line}",
        "reply_markup": InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Удалить", callback_data=f"delpayok:{repayment.id}"
                    ),
                    InlineKeyboardButton(text="↩️ Отмена", callback_data=f"delpayno:{repayment.id}"),
                ]
            ]
        ),
        "parse_mode": ParseMode.HTML,
        "disable_web_page_preview": True,
    }
