"""Repayment flow: /pay FSM, /payments ledger, delete-with-confirm (executor only)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.adapters.telegram.fsm import RepaymentStates
from src.adapters.telegram.keyboards import (
    BTN_PAY,
    BTN_PAYMENTS,
    debt_menu_keyboard,
    main_menu_keyboard,
)
from src.adapters.telegram.payments import payments_message, repayment_confirm_message
from src.domain.entities import Repayment
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository, IManualDebtRepository, IRepaymentRepository
from src.domain.value_objects import Money, parse_price_to_kop
from src.infrastructure.config import Settings
from src.use_cases.add_repayment import AddRepaymentRequest, AddRepaymentUseCase
from src.use_cases.calc_balance import CalcBalanceUseCase
from src.use_cases.delete_repayment import DeleteRepaymentRequest, DeleteRepaymentUseCase
from src.use_cases.list_repayments import ListRepaymentsUseCase

_PAY_PROMPT = "💸 Сколько заказчик отдал? Введи сумму (например, 1 299,50). /cancel — отмена."
_DENIED = "Погашение вносит только исполнитель 😉"
_DELETE_DENIED = "Удалять погашения может только исполнитель 😉"


def _author_names(settings: Settings) -> dict[int, str]:
    return {settings.executor_id: "исполнитель", settings.customer_id: "заказчик"}


def _balance_tail(balance_kop: int, advance_kop: int) -> str:
    if advance_kop:
        return f"Остаток: 0,00 BYN · 🎁 аванс {Money(advance_kop).format_rub()}"
    return f"Остаток долга: {Money(balance_kop).format_rub()}"


async def _find(repo: IRepaymentRepository, repayment_id: int) -> Repayment | None:
    return next((r for r in await repo.list_all() if r.id == repayment_id), None)


async def _send_ledger(
    message: Message, repayment_repo: IRepaymentRepository, settings: Settings, user_id: int
) -> None:
    response = await ListRepaymentsUseCase(repayment_repo).execute()
    await message.answer(
        **payments_message(
            response,
            for_executor=user_id == settings.executor_id,
            author_names=_author_names(settings),
        )
    )


def build_repayments_router(settings: Settings) -> Router:
    router = Router(name="repayments")
    executor_id = settings.executor_id

    async def begin_pay(message: Message, state: FSMContext) -> None:
        if message.from_user is None or message.from_user.id != executor_id:
            await message.answer(_DENIED, reply_markup=main_menu_keyboard())
            return
        await state.set_state(RepaymentStates.waiting_amount)
        await message.answer(_PAY_PROMPT)

    async def save(
        state: FSMContext,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_repo: IManualDebtRepository,
        *,
        amount_kop: int,
        note: str | None,
    ) -> str:
        await state.clear()
        saved = await AddRepaymentUseCase(repayment_repo).execute(
            AddRepaymentRequest(amount_kop=amount_kop, created_by=executor_id, note=note)
        )
        balance = await CalcBalanceUseCase(item_repo, repayment_repo, manual_repo).execute()
        amount = Money(saved.repayment.amount_kop).format_rub()
        tail = _balance_tail(balance.balance_kop, balance.advance_kop)
        return f"✅ Записал погашение {amount}.\n{tail}"

    async def render_ledger(callback: CallbackQuery, repayment_repo: IRepaymentRepository) -> None:
        if not isinstance(callback.message, Message):
            await callback.answer("Сообщение недоступно.", show_alert=True)
            return
        response = await ListRepaymentsUseCase(repayment_repo).execute()
        try:
            await callback.message.edit_text(
                **payments_message(
                    response, for_executor=True, author_names=_author_names(settings)
                )
            )
        except TelegramBadRequest as exc:
            # Same content as before => Telegram refuses the edit; that's fine.
            if "not modified" not in exc.message.lower():
                raise

    @router.message(Command("pay"))
    async def cmd_pay(message: Message, state: FSMContext) -> None:
        await state.clear()
        await begin_pay(message, state)

    @router.message(F.text == BTN_PAY)
    async def btn_pay(message: Message, state: FSMContext) -> None:
        await state.clear()
        await begin_pay(message, state)

    @router.message(Command("payments"))
    async def cmd_payments(
        message: Message, state: FSMContext, repayment_repo: IRepaymentRepository
    ) -> None:
        await state.clear()
        assert message.from_user is not None
        await _send_ledger(message, repayment_repo, settings, message.from_user.id)

    @router.message(F.text == BTN_PAYMENTS)
    async def btn_payments(
        message: Message, state: FSMContext, repayment_repo: IRepaymentRepository
    ) -> None:
        await state.clear()
        assert message.from_user is not None
        await _send_ledger(message, repayment_repo, settings, message.from_user.id)

    @router.message(RepaymentStates.waiting_amount, F.text)
    async def receive_amount(message: Message, state: FSMContext) -> None:
        assert message.text is not None
        try:
            amount_kop = parse_price_to_kop(message.text)
        except DomainError as exc:
            await message.answer(f"Не похоже на сумму: {exc}\nПопробуй еще раз или /cancel.")
            return
        if amount_kop <= 0:
            await message.answer("Сумма должна быть больше нуля. Попробуй еще раз или /cancel.")
            return
        await state.set_state(RepaymentStates.waiting_note)
        await state.update_data(amount_kop=amount_kop)
        await message.answer(
            "Добавь комментарий к погашению или нажми кнопку ниже. /cancel — отмена.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="➡️ Без комментария", callback_data="paynonote")]
                ]
            ),
        )

    @router.message(RepaymentStates.waiting_note, F.text)
    async def receive_note(
        message: Message,
        state: FSMContext,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_debt_repo: IManualDebtRepository,
    ) -> None:
        assert message.text is not None
        data = await state.get_data()
        reply = await save(
            state,
            item_repo,
            repayment_repo,
            manual_debt_repo,
            amount_kop=int(data["amount_kop"]),
            note=message.text,
        )
        await message.answer(reply, reply_markup=debt_menu_keyboard(for_executor=True))

    @router.callback_query(F.data == "paynonote", F.from_user.id == executor_id)
    async def skip_note(
        callback: CallbackQuery,
        state: FSMContext,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_debt_repo: IManualDebtRepository,
    ) -> None:
        data = await state.get_data()
        if "amount_kop" not in data:
            await callback.answer("Начни заново: /pay", show_alert=True)
            return
        reply = await save(
            state,
            item_repo,
            repayment_repo,
            manual_debt_repo,
            amount_kop=int(data["amount_kop"]),
            note=None,
        )
        if isinstance(callback.message, Message):
            await callback.message.answer(reply, reply_markup=debt_menu_keyboard(for_executor=True))
        await callback.answer()

    @router.callback_query(F.data == "paynonote")
    async def skip_note_denied(callback: CallbackQuery) -> None:
        await callback.answer(_DENIED, show_alert=True)

    @router.callback_query(F.data.startswith("delpay:"), F.from_user.id == executor_id)
    async def ask_delete(callback: CallbackQuery, repayment_repo: IRepaymentRepository) -> None:
        assert callback.data is not None
        if not isinstance(callback.message, Message):
            await callback.answer("Сообщение недоступно.", show_alert=True)
            return
        try:
            repayment_id = int(callback.data.split(":")[1])
        except (IndexError, ValueError):
            await callback.answer("Битые данные кнопки.", show_alert=True)
            return
        repayment = await _find(repayment_repo, repayment_id)
        if repayment is None:
            await callback.answer("Запись не найдена.", show_alert=True)
            return
        who = _author_names(settings).get(repayment.created_by, "—")
        await callback.message.edit_text(**repayment_confirm_message(repayment, who=who))
        await callback.answer("Подтверди удаление")

    @router.callback_query(F.data.startswith("delpayok:"), F.from_user.id == executor_id)
    async def confirm_delete(callback: CallbackQuery, repayment_repo: IRepaymentRepository) -> None:
        assert callback.data is not None
        if not isinstance(callback.message, Message):
            await callback.answer("Сообщение недоступно.", show_alert=True)
            return
        try:
            repayment_id = int(callback.data.split(":")[1])
        except (IndexError, ValueError):
            await callback.answer("Битые данные кнопки.", show_alert=True)
            return
        try:
            await DeleteRepaymentUseCase(repayment_repo).execute(
                DeleteRepaymentRequest(repayment_id=repayment_id)
            )
        except DomainError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        await render_ledger(callback, repayment_repo)
        await callback.answer("Удалено 🗑")

    @router.callback_query(F.data.startswith("delpayno:"), F.from_user.id == executor_id)
    async def cancel_delete(callback: CallbackQuery, repayment_repo: IRepaymentRepository) -> None:
        await render_ledger(callback, repayment_repo)
        await callback.answer()

    @router.callback_query(F.data.startswith("delpay"))
    async def delete_denied(callback: CallbackQuery) -> None:
        await callback.answer(_DELETE_DENIED, show_alert=True)

    return router
