"""Basic commands: /start, /list, /cancel."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.adapters.telegram.cards import format_item_line
from src.domain.interfaces import IItemRepository
from src.infrastructure.config import Settings


def build_start_router(settings: Settings) -> Router:
    router = Router(name="start")

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        role = "son (manager)" if user_id == settings.son_id else "dad (sender)"
        await message.answer(
            "👋 Hi! I'm the family Ozon tracker.\n"
            f"Your role: {role}.\n\n"
            "Send an Ozon link and I'll track it.\n"
            "Commands: /list — recent items."
        )

    @router.message(Command("cancel"))
    async def cmd_cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Cancelled. Send an Ozon link or use /list.")

    @router.message(Command("list"))
    async def cmd_list(message: Message, item_repo: IItemRepository) -> None:
        items = await item_repo.list_recent(limit=10)
        if not items:
            await message.answer("No items yet. Send an Ozon link to start.")
            return
        await message.answer("\n".join(format_item_line(item) for item in items))

    @router.message(F.text.startswith("/debt"))
    async def cmd_debt_stub(message: Message) -> None:
        await message.answer("💰 Debt calculation lands in P2 (SPEC-002).")

    return router
