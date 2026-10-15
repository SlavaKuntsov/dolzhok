"""Basic commands: /start, /list, /cancel + reply-menu buttons."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.adapters.telegram.cards import format_item_card
from src.adapters.telegram.keyboards import (
    BTN_CANCEL,
    BTN_DEBT,
    BTN_LIST,
    BTN_STATS,
    item_keyboard,
    main_menu_keyboard,
)
from src.domain.interfaces import IItemRepository
from src.infrastructure.config import Settings


async def _send_list(message: Message, item_repo: IItemRepository, *, for_son: bool) -> None:
    items = await item_repo.list_recent(limit=10)
    if not items:
        await message.answer(
            "Пока пусто. Пришли ссылку на Ozon, чтобы начать.", reply_markup=main_menu_keyboard()
        )
        return
    for item in items:
        await message.answer(
            format_item_card(item),
            reply_markup=item_keyboard(item, for_son=for_son),
            disable_web_page_preview=True,
        )


async def _send_debt_stub(message: Message) -> None:
    await message.answer(
        "💰 Подсчет долга появится в P2 (SPEC-002).", reply_markup=main_menu_keyboard()
    )


async def _send_stats_stub(message: Message) -> None:
    await message.answer(
        "📊 Статистика появится в P2 (SPEC-002).", reply_markup=main_menu_keyboard()
    )


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
    async def cmd_debt_stub(message: Message, state: FSMContext) -> None:
        await state.clear()
        await _send_debt_stub(message)

    @router.message(F.text == BTN_DEBT)
    async def btn_debt_stub(message: Message, state: FSMContext) -> None:
        await state.clear()
        await _send_debt_stub(message)

    @router.message(F.text.startswith("/stats"))
    async def cmd_stats_stub(message: Message, state: FSMContext) -> None:
        await state.clear()
        await _send_stats_stub(message)

    @router.message(F.text == BTN_STATS)
    async def btn_stats_stub(message: Message, state: FSMContext) -> None:
        await state.clear()
        await _send_stats_stub(message)

    return router
