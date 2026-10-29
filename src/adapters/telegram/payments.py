"""Repayment views: debt balance text, ledger list, delete confirmation."""

from __future__ import annotations

import html
from collections.abc import Mapping
from typing import Any

from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.adapters.telegram.keyboards import debt_menu_keyboard
from src.domain.entities import Repayment
from src.domain.interfaces import IItemRepository, IManualDebtRepository, IRepaymentRepository
from src.domain.value_objects import Money, format_signed_rub
from src.use_cases.calc_balance import CalcBalanceResponse, CalcBalanceUseCase
from src.use_cases.calc_debt import CalcDebtResponse, CalcDebtUseCase
from src.use_cases.list_repayments import ListRepaymentsResponse


def _money(kop: int) -> str:
    return Money(kop).format_rub()


def _signed_money(kop: int) -> str:
    """Like `_money` but permits negative balances (past-debt overpayment)."""
    return format_signed_rub(kop)


def format_debt_text(
    debt: CalcDebtResponse, balance: CalcBalanceResponse, *, for_executor: bool
) -> str:
    """Debt summary: owed, postpaid, past orders, total, repaid, remaining.

    The executor also sees the breakdown between items and past-orders debt;
    the customer only sees the total. Blocks are separated by a blank line so
    the accrual side (what is owed for goods) reads apart from the running
    balance (what is left after repayments).
    """
    head = []
    if for_executor:
        head.append(
            f"💰 Долг по товарам: {_money(balance.debt_kop)} (предоплата, {balance.debt_count} шт)"
        )
    else:
        head.append(f"💰 Долг: {_signed_money(balance.total_kop)}")
    if debt.postpaid_count:
        head.append(f"⏳ Ждет постоплаты: {_money(debt.postpaid_kop)} ({debt.postpaid_count} шт)")

    totals = []
    if for_executor:
        totals.append(f"🧾 Итого долг: {_signed_money(balance.total_kop)}")
    if balance.repaid_count:
        totals.append(f"💸 Погашено: {_money(balance.repaid_kop)} ({balance.repaid_count} шт)")
    if balance.advance_kop:
        totals.append("✅ Остаток: 0,00 BYN")
        totals.append(f"🎁 Аванс: {_money(balance.advance_kop)}")
    elif balance.total_kop or balance.repaid_count or balance.debt_count or balance.manual_kop:
        totals.append(f"✅ Остаток: {_signed_money(balance.balance_kop)}")

    blocks = [head]
    if for_executor:
        blocks.append([f"📜 Долги за прошлое: {_signed_money(balance.manual_kop)}"])
    if totals:
        blocks.append(totals)
    return "\n\n".join("\n".join(block) for block in blocks)


async def send_debt(
    message: Message,
    item_repo: IItemRepository,
    repayment_repo: IRepaymentRepository,
    manual_repo: IManualDebtRepository,
    *,
    for_executor: bool,
) -> None:
    """Render the debt summary + the debt submenu keyboard."""
    debt = await CalcDebtUseCase(item_repo, manual_repo).execute()
    balance = await CalcBalanceUseCase(item_repo, repayment_repo, manual_repo).execute()
    await message.answer(
        format_debt_text(debt, balance, for_executor=for_executor),
        reply_markup=debt_menu_keyboard(for_executor=for_executor),
    )


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
    for_executor: bool,
    author_names: Mapping[int, str],
) -> dict[str, Any]:
    """Ready-to-splat kwargs for the ledger list; executor gets a 🗑 per entry.

    Executor always receives an inline keyboard (possibly empty) so that re-rendering
    over a message with delete buttons actually clears them — Telegram keeps the
    old markup when ``reply_markup`` is omitted.
    """
    keyboard: InlineKeyboardMarkup | None = None
    if for_executor:
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
    """Ready-to-splat kwargs asking executor to confirm deletion of one entry."""
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
