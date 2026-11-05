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
    """Debt summary: what is already paid (by payment type), pending, and the rest.

    Only work-in-progress money is shown, split by how it settles: the executor
    sees what they already fronted (debt) broken down into prepaid and received
    postpaid, plus what is still on its way (pending postpaid, not owed yet).
    The gross accrual and the repaid ledger are deliberately absent — the
    running balance is the only total that answers "how much is left".
    """
    paid = []
    if for_executor:
        paid.append(f"💰 Уже оплачено за товары: {_money(balance.debt_kop)}")
        if balance.debt_prepaid_kop:
            paid.append(
                f"  • предоплата: {_money(balance.debt_prepaid_kop)} "
                f"({balance.debt_prepaid_count} шт)"
            )
        if balance.debt_postpaid_kop:
            paid.append(
                f"  • постоплата: {_money(balance.debt_postpaid_kop)} "
                f"({balance.debt_postpaid_count} шт)"
            )
    else:
        paid.append(f"💰 Долг: {_signed_money(balance.total_kop)}")

    pending = []
    if debt.pending_kop:
        pending.append(
            f"⏳ Будет оплачено при получении: {_money(debt.pending_kop)} ({debt.pending_count} шт)"
        )

    remaining = []
    if balance.advance_kop:
        remaining.append("✅ Остаток: 0,00 BYN")
        remaining.append(f"🎁 Аванс: {_money(balance.advance_kop)}")
    elif balance.total_kop or balance.debt_count or balance.manual_kop:
        remaining.append(f"✅ Остаток: {_signed_money(balance.balance_kop)}")

    blocks = [paid]
    if for_executor:
        blocks.append([f"📜 Долги за прошлое: {_signed_money(balance.manual_kop)}"])
    blocks += [block for block in (pending, remaining) if block]
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
