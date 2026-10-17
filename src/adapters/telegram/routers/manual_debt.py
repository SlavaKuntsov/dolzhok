"""Manual past-orders debt: add/subtract, overwrite, reset (executor only)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.adapters.telegram.fsm import ManualDebtStates
from src.adapters.telegram.keyboards import (
    BTN_MANUAL_ADD,
    BTN_MANUAL_EDIT,
    BTN_MANUAL_RESET,
    main_menu_keyboard,
)
from src.adapters.telegram.payments import send_debt
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository, IManualDebtRepository, IRepaymentRepository
from src.domain.value_objects import format_signed_rub, parse_signed_price_to_kop
from src.infrastructure.config import Settings
from src.use_cases.adjust_manual_debt import AdjustManualDebtRequest, AdjustManualDebtUseCase
from src.use_cases.set_manual_debt import SetManualDebtRequest, SetManualDebtUseCase

_ADD_PROMPT = (
    "➕ На сколько изменить долг за прошлое?\n"
    "Введи сумму (например, 1 500). С минусом — вычесть: -500.\n"
    "/cancel — отмена."
)
_EDIT_PROMPT = (
    "✏️ Введи новую сумму долга за прошлое (например, 1 500). "
    "С минусом — если за прошлое переплатили: -500.\n/cancel — отмена."
)
_DENIED = "Долг за прошлое меняет только исполнитель 😉"
_RESET_DENIED = "Сбрасывать долг может только исполнитель 😉"
_BAD_AMOUNT = "Не похоже на сумму"


def build_manual_debt_router(settings: Settings) -> Router:
    router = Router(name="manual_debt")
    executor_id = settings.executor_id

    async def _show(
        message: Message,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_repo: IManualDebtRepository,
    ) -> None:
        await send_debt(
            message, item_repo, repayment_repo, manual_repo, for_executor=True
        )

    async def _save(
        message: Message,
        state: FSMContext,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_repo: IManualDebtRepository,
        *,
        amount_kop: int,
        overwrite: bool,
    ) -> None:
        try:
            if overwrite:
                saved = await SetManualDebtUseCase(manual_repo).execute(
                    SetManualDebtRequest(amount_kop=amount_kop)
                )
                amount = saved.manual_debt.amount_kop
            else:
                adjusted = await AdjustManualDebtUseCase(manual_repo).execute(
                    AdjustManualDebtRequest(delta_kop=amount_kop)
                )
                amount = adjusted.manual_debt.amount_kop
        except DomainError as exc:
            await message.answer(f"Не получилось: {exc}\nПопробуй еще раз или /cancel.")
            return
        await state.clear()
        await message.answer(f"✅ Долг за прошлое: {format_signed_rub(amount)}")
        await _show(message, item_repo, repayment_repo, manual_repo)

    @router.message(F.text == BTN_MANUAL_ADD, F.from_user.id == executor_id)
    async def ask_add(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(ManualDebtStates.waiting_amount)
        await message.answer(_ADD_PROMPT)

    @router.message(F.text == BTN_MANUAL_EDIT, F.from_user.id == executor_id)
    async def ask_edit(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(ManualDebtStates.waiting_total)
        await message.answer(_EDIT_PROMPT)

    @router.message(F.text == BTN_MANUAL_RESET, F.from_user.id == executor_id)
    async def ask_reset(
        message: Message, state: FSMContext, manual_debt_repo: IManualDebtRepository
    ) -> None:
        await state.clear()
        current = await manual_debt_repo.get()
        await message.answer(
            f"🗑 Сбросить долг за прошлое ({format_signed_rub(current.amount_kop)})?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Сбросить", callback_data="mdreset:ok"),
                        InlineKeyboardButton(text="↩️ Отмена", callback_data="mdreset:no"),
                    ]
                ]
            ),
        )

    @router.message(ManualDebtStates.waiting_amount, F.text)
    async def receive_amount(
        message: Message,
        state: FSMContext,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_debt_repo: IManualDebtRepository,
    ) -> None:
        assert message.text is not None
        try:
            delta_kop = parse_signed_price_to_kop(message.text)
        except DomainError as exc:
            await message.answer(f"{_BAD_AMOUNT}: {exc}\nПопробуй еще раз или /cancel.")
            return
        if delta_kop == 0:
            await message.answer("Сумма не может быть нулевой. Попробуй еще раз или /cancel.")
            return
        await _save(
            message,
            state,
            item_repo,
            repayment_repo,
            manual_debt_repo,
            amount_kop=delta_kop,
            overwrite=False,
        )

    @router.message(ManualDebtStates.waiting_total, F.text)
    async def receive_total(
        message: Message,
        state: FSMContext,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_debt_repo: IManualDebtRepository,
    ) -> None:
        assert message.text is not None
        try:
            amount_kop = parse_signed_price_to_kop(message.text)
        except DomainError as exc:
            await message.answer(f"{_BAD_AMOUNT}: {exc}\nПопробуй еще раз или /cancel.")
            return
        await _save(
            message,
            state,
            item_repo,
            repayment_repo,
            manual_debt_repo,
            amount_kop=amount_kop,
            overwrite=True,
        )

    @router.callback_query(F.data == "mdreset:ok", F.from_user.id == executor_id)
    async def confirm_reset(
        callback: CallbackQuery,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_debt_repo: IManualDebtRepository,
    ) -> None:
        await SetManualDebtUseCase(manual_debt_repo).execute(SetManualDebtRequest(amount_kop=0))
        if isinstance(callback.message, Message):
            await callback.message.answer("🗑 Долг за прошлое сброшен: 0,00 BYN")
            await _show(callback.message, item_repo, repayment_repo, manual_debt_repo)
        await callback.answer("Сброшено")

    @router.callback_query(F.data == "mdreset:no", F.from_user.id == executor_id)
    async def cancel_reset(callback: CallbackQuery) -> None:
        await callback.answer("Отменено")

    @router.message(F.text.in_({BTN_MANUAL_ADD, BTN_MANUAL_EDIT, BTN_MANUAL_RESET}))
    async def manual_debt_denied(message: Message) -> None:
        await message.answer(_DENIED, reply_markup=main_menu_keyboard())

    @router.callback_query(F.data.startswith("mdreset:"))
    async def reset_denied(callback: CallbackQuery) -> None:
        await callback.answer(_RESET_DENIED, show_alert=True)

    return router
