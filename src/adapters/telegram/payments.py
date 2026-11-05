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
from src.use_cases.list_repayments import ListRepaymentsResponse


def _money(kop: int) -> str:
    return Money(kop).format_rub()


def _signed_money(kop: int) -> str:
    """Like `_money` but permits negative balances (past-debt overpayment)."""
    return format_signed_rub(kop)


def _pieces(parts: list[tuple[str, int]]) -> str:
    """Render ``[("уже у меня", 6), ("в пути", 3)]`` as ``6 уже у меня, 3 в пути``."""
    return ", ".join(f"{count} {label}" for label, count in parts if count)


def format_debt_text(balance: CalcBalanceResponse, *, for_executor: bool) -> str:
    """Debt summary: what is already paid, what is not owed yet, what is left.

    Every quantity carries its own explanation, because the same kopecks mean
    different things on different lines: the executor sees what they fronted
    (debt) split by how it was paid — and, within the prepaid part, how much is
    already in hand versus still in transit — then what is not debt yet, then
    the running balance with the arithmetic that produced it. Work items
    without a price are called out: dropping them silently is the bug this
    summary exists to prevent.
    """
    debt = balance.debt
    head = []
    if for_executor:
        head.append(f"💰 Долг за товары: {_money(debt.debt.amount_kop)}")
        prepaid = debt.debt_prepaid
        if prepaid.amount_kop:
            detail = _pieces(
                [
                    ("уже у меня", debt.prepaid_received.count),
                    ("в пути", debt.prepaid_ordered.count),
                ]
            )
            head.append(
                f"  • заплатил заранее: {_money(prepaid.amount_kop)} ({prepaid.count} шт: {detail})"
            )
        postpaid = debt.debt_postpaid
        if postpaid.amount_kop:
            head.append(
                f"  • заплатил при получении: {_money(postpaid.amount_kop)} ({postpaid.count} шт)"
            )
    else:
        head.append(f"💰 Долг: {_signed_money(balance.total_kop)}")

    pending = []
    if debt.pending.amount_kop:
        pending.append(
            f"⏳ Ещё не долг, оплачу при получении: {_money(debt.pending.amount_kop)} "
            f"({debt.pending.count} шт)"
        )

    unpriced = []
    if debt.unpriced_count:
        unpriced.append(f"⚠️ Без цены: {debt.unpriced_count} шт — в долг не входят")

    remaining = []
    if balance.advance_kop:
        remaining.append("✅ Остаток: 0,00 BYN")
        remaining.append(f"🎁 Аванс: {_money(balance.advance_kop)}")
    elif balance.total_kop or debt.debt.count or debt.manual_kop:
        remaining.append(f"✅ Остаток: {_signed_money(balance.balance_kop)}")
    if remaining and for_executor and (balance.repaid_count or debt.manual_kop):
        # Show the subtraction whenever the remaining figure is not just the
        # goods total — repayments and/or the past-orders line are in play.
        remaining.append(
            f"   долг {_money(balance.total_kop)} − погашено {_money(balance.repaid_kop)}"
        )

    blocks = [head]
    if for_executor:
        blocks.append([f"📜 Долги за прошлое: {_signed_money(debt.manual_kop)}"])
    blocks += [block for block in (pending, unpriced, remaining) if block]
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
    balance = await CalcBalanceUseCase(item_repo, repayment_repo, manual_repo).execute()
    await message.answer(
        format_debt_text(balance, for_executor=for_executor),
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
