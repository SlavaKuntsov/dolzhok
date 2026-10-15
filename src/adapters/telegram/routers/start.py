"""Basic commands: /start, /list, /cancel + reply-menu buttons."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.adapters.telegram.cards import card_message
from src.adapters.telegram.keyboards import (
    BTN_BACK,
    BTN_CANCEL,
    BTN_DEBT,
    BTN_DEBTS,
    BTN_LIST,
    BTN_STATS,
    debt_menu_keyboard,
    main_menu_keyboard,
)
from src.adapters.telegram.lists import list_page_message
from src.adapters.telegram.payments import format_debt_text
from src.domain.entities import ItemStatus
from src.domain.interfaces import IItemRepository, IRepaymentRepository
from src.domain.value_objects import Money
from src.infrastructure.config import Settings
from src.use_cases.calc_balance import CalcBalanceUseCase
from src.use_cases.calc_debt import CalcDebtUseCase
from src.use_cases.calc_stats import CalcStatsUseCase
from src.use_cases.list_items import ListItemsRequest, ListItemsUseCase


def _parse_filter(raw: str) -> ItemStatus | None:
    """`ALL` -> None (no filter); a status name -> that status."""
    return None if raw == "ALL" else ItemStatus(raw)


async def _render_list(
    message: Message,
    item_repo: IItemRepository,
    *,
    status: ItemStatus | None = None,
    page: int = 0,
    edit: bool = False,
) -> None:
    response = await ListItemsUseCase(item_repo).execute(ListItemsRequest(status=status, page=page))
    kwargs = list_page_message(response)
    if edit:
        try:
            await message.edit_text(**kwargs)
        except TelegramBadRequest as exc:
            # Identical page/filter => Telegram refuses the edit; ignore only that,
            # surface real failures (stale/deleted message) to the framework.
            if "not modified" not in exc.message.lower():
                raise
            return
    else:
        await message.answer(**kwargs)


async def _list_callback(
    callback: CallbackQuery,
    item_repo: IItemRepository,
    state: FSMContext,
    *,
    raw_filter: str,
    page: int,
) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer("Сообщение недоступно.", show_alert=True)
        return
    try:
        status = _parse_filter(raw_filter)
    except ValueError:
        await callback.answer("Битые данные кнопки.", show_alert=True)
        return
    # Navigating the list abandons any armed price/qty entry (same as /list).
    await state.clear()
    await _render_list(callback.message, item_repo, status=status, page=page, edit=True)
    await callback.answer()


async def _send_debt(
    message: Message,
    item_repo: IItemRepository,
    repayment_repo: IRepaymentRepository,
    *,
    for_son: bool,
) -> None:
    debt = await CalcDebtUseCase(item_repo).execute()
    balance = await CalcBalanceUseCase(item_repo, repayment_repo).execute()
    await message.answer(
        format_debt_text(debt, balance), reply_markup=debt_menu_keyboard(for_son=for_son)
    )


async def _send_stats(message: Message, item_repo: IItemRepository) -> None:
    stats = await CalcStatsUseCase(item_repo).execute()
    lines = [
        "📊 Статистика",
        f"Всего: {stats.total}",
        f"🆕 Новых: {stats.new}",
        f"📦 Заказано: {stats.ordered}",
        f"✅ Получено: {stats.received}",
        f"🚫 Отменено: {stats.cancelled}",
    ]
    if stats.returns_count:
        returned = Money(stats.returns_kop).format_rub()
        lines.append(f"↩️ Возвраты: {stats.returns_count} · {returned}")
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


async def _cancel_state(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Отменено. Пришли ссылку Ozon или нажми кнопку ниже.",
        reply_markup=main_menu_keyboard(),
    )


def build_start_router(settings: Settings) -> Router:
    router = Router(name="start")
    son_id = settings.son_id

    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        user_id = message.from_user.id if message.from_user else None
        role = (
            "сын (управляешь заказами)"
            if user_id == settings.son_id
            else "папа (присылаешь ссылки)"
        )
        await message.answer(
            "👋 Привет! Я семейный трекер заказов Ozon.\n"
            f"Твоя роль: {role}.\n\n"
            "Пришли ссылку на товар — я его запомню.\n"
            "Кнопки внизу: список товаров и раздел «Долги».",
            reply_markup=main_menu_keyboard(),
        )

    @router.message(Command("cancel"))
    async def cmd_cancel(message: Message, state: FSMContext) -> None:
        await _cancel_state(message, state)

    @router.message(F.text == BTN_CANCEL)
    async def btn_cancel(message: Message, state: FSMContext) -> None:
        await _cancel_state(message, state)

    @router.message(Command("menu"))
    async def cmd_menu(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Меню действий:", reply_markup=main_menu_keyboard())

    @router.message(Command("list"))
    async def cmd_list(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _render_list(message, item_repo)

    @router.message(F.text == BTN_LIST)
    async def btn_list(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _render_list(message, item_repo)

    @router.message(F.text == BTN_DEBTS)
    async def btn_debts(message: Message, state: FSMContext) -> None:
        await state.clear()
        assert message.from_user is not None
        await message.answer(
            "💰 Долги — выбери действие:",
            reply_markup=debt_menu_keyboard(for_son=message.from_user.id == son_id),
        )

    @router.message(F.text == BTN_BACK)
    async def btn_back(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu_keyboard())

    @router.message(F.text.startswith("/debt"))
    async def cmd_debt(
        message: Message,
        state: FSMContext,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
    ) -> None:
        await state.clear()
        assert message.from_user is not None
        await _send_debt(
            message,
            item_repo,
            repayment_repo,
            for_son=message.from_user.id == son_id,
        )

    @router.message(F.text == BTN_DEBT)
    async def btn_debt(
        message: Message,
        state: FSMContext,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
    ) -> None:
        await state.clear()
        assert message.from_user is not None
        await _send_debt(
            message,
            item_repo,
            repayment_repo,
            for_son=message.from_user.id == son_id,
        )

    @router.message(F.text.startswith("/stats"))
    async def cmd_stats(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _send_stats(message, item_repo)

    @router.message(F.text == BTN_STATS)
    async def btn_stats(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _send_stats(message, item_repo)

    @router.callback_query(F.data.startswith("lf:"))
    async def list_filter(
        callback: CallbackQuery, item_repo: IItemRepository, state: FSMContext
    ) -> None:
        raw_filter = (callback.data or "").partition(":")[2]
        await _list_callback(callback, item_repo, state, raw_filter=raw_filter, page=0)

    @router.callback_query(F.data.startswith("lp:"))
    async def list_page(
        callback: CallbackQuery, item_repo: IItemRepository, state: FSMContext
    ) -> None:
        assert callback.data is not None
        try:
            _, raw_filter, raw_page = callback.data.split(":")
            page = int(raw_page)
        except ValueError:
            await callback.answer("Битые данные кнопки.", show_alert=True)
            return
        await _list_callback(callback, item_repo, state, raw_filter=raw_filter, page=page)

    @router.callback_query(F.data.startswith("nooplist:"))
    async def list_noop(callback: CallbackQuery) -> None:
        await callback.answer()

    @router.callback_query(F.data.startswith("view:"))
    async def view_item(
        callback: CallbackQuery, item_repo: IItemRepository, state: FSMContext
    ) -> None:
        assert callback.data is not None
        if not isinstance(callback.message, Message):
            await callback.answer("Сообщение недоступно.", show_alert=True)
            return
        try:
            item_id = int(callback.data.split(":")[1])
        except (IndexError, ValueError):
            await callback.answer("Битые данные кнопки.", show_alert=True)
            return
        item = await item_repo.get_by_id(item_id)
        if item is None:
            await callback.answer("Товар не найден.", show_alert=True)
            return
        await state.clear()
        for_son = callback.from_user.id == son_id
        await callback.message.answer(**card_message(item, for_son=for_son))
        await callback.answer()

    return router
