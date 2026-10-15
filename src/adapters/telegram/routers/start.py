"""Basic commands: /start, /list, /cancel + reply-menu buttons."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.adapters.telegram.cards import card_message
from src.adapters.telegram.keyboards import (
    BTN_CANCEL,
    BTN_DEBT,
    BTN_LIST,
    BTN_STATS,
    main_menu_keyboard,
)
from src.domain.interfaces import IItemRepository
from src.domain.value_objects import Money
from src.infrastructure.config import Settings
from src.use_cases.calc_debt import CalcDebtUseCase
from src.use_cases.calc_stats import CalcStatsUseCase


async def _send_list(message: Message, item_repo: IItemRepository, *, for_son: bool) -> None:
    items = await item_repo.list_recent(limit=10)
    if not items:
        await message.answer(
            "Пока пусто. Пришли ссылку на Ozon, чтобы начать.", reply_markup=main_menu_keyboard()
        )
        return
    for item in items:
        await message.answer(**card_message(item, for_son=for_son))


async def _send_debt(message: Message, item_repo: IItemRepository) -> None:
    summary = await CalcDebtUseCase(item_repo).execute()
    debt = Money(summary.debt_kop).format_rub() if summary.debt_count else "0 BYN"
    lines = [f"💰 Папа должен: {debt} (предоплата, {summary.debt_count} шт)"]
    if summary.postpaid_count:
        pending = Money(summary.postpaid_kop).format_rub()
        lines.append(f"⏳ Ждет постоплаты: {pending} ({summary.postpaid_count} шт)")
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


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

    def _is_son(message: Message) -> bool:
        return message.from_user is not None and message.from_user.id == son_id

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
            "Кнопки внизу: список товаров и долг.",
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
        await _send_list(message, item_repo, for_son=_is_son(message))

    @router.message(F.text == BTN_LIST)
    async def btn_list(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _send_list(message, item_repo, for_son=_is_son(message))

    @router.message(F.text.startswith("/debt"))
    async def cmd_debt(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _send_debt(message, item_repo)

    @router.message(F.text == BTN_DEBT)
    async def btn_debt(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _send_debt(message, item_repo)

    @router.message(F.text.startswith("/stats"))
    async def cmd_stats(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _send_stats(message, item_repo)

    @router.message(F.text == BTN_STATS)
    async def btn_stats(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        await state.clear()
        await _send_stats(message, item_repo)

    return router
