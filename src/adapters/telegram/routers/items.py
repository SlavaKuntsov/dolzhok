"""Item flow: ingest Ozon links, price FSM, status buttons (son only)."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.adapters.telegram.cards import format_item_card
from src.adapters.telegram.fsm import PriceStates
from src.adapters.telegram.keyboards import item_keyboard
from src.domain import ozon
from src.domain.entities import ItemStatus
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository, IUrlResolver
from src.infrastructure.config import Settings
from src.use_cases.add_item import AddItemRequest, AddItemUseCase
from src.use_cases.change_status import ChangeStatusRequest, ChangeStatusUseCase
from src.use_cases.set_price import SetPriceRequest, SetPriceUseCase

logger = logging.getLogger(__name__)


def build_items_router(settings: Settings) -> Router:
    router = Router(name="items")
    son_id = settings.son_id

    @router.message(F.text)
    async def ingest_link(
        message: Message,
        bot: Bot,
        item_repo: IItemRepository,
        url_resolver: IUrlResolver,
    ) -> None:
        assert message.text is not None
        assert message.from_user is not None
        urls = [u for u in ozon.extract_urls(message.text) if ozon.is_ozon_url(u)]
        if not urls:
            if "http" in message.text:
                await message.answer("I only track Ozon links (ozon.ru / ozo.ru) 🔗")
            return
        try:
            response = await AddItemUseCase(item_repo, url_resolver).execute(
                AddItemRequest(raw_url=urls[0], from_user_id=message.from_user.id)
            )
        except DomainError as exc:
            await message.answer(f"Couldn't save this link: {exc}")
            return
        item = response.item
        if message.from_user.id == son_id:
            await message.answer(
                format_item_card(item), reply_markup=item_keyboard(item, for_son=True)
            )
            return
        status = "saved" if response.created else "already tracking"
        await message.answer(f"Got it, {status} #{item.id} ✅\nSon will take it from here.")
        await bot.send_message(
            son_id, format_item_card(item), reply_markup=item_keyboard(item, for_son=True)
        )

    @router.callback_query(F.data.startswith("price:"), F.from_user.id == son_id)
    async def ask_price(
        callback: CallbackQuery, state: FSMContext, item_repo: IItemRepository
    ) -> None:
        assert callback.data is not None
        if not isinstance(callback.message, Message):
            await callback.answer("Message not available.", show_alert=True)
            return
        try:
            item_id = int(callback.data.split(":")[1])
        except (IndexError, ValueError):
            await callback.answer("Bad button payload.", show_alert=True)
            return
        item = await item_repo.get_by_id(item_id)
        if item is None or item.is_closed:
            await callback.answer("Item not available.", show_alert=True)
            return
        await state.set_state(PriceStates.waiting_price)
        await state.update_data(item_id=item_id)
        await callback.message.answer(
            f"Send the price for #{item_id} (e.g. 1 299,50). /cancel to abort."
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("price:"))
    async def ask_price_denied(callback: CallbackQuery) -> None:
        await callback.answer("Only son can set prices 😉", show_alert=True)

    @router.message(PriceStates.waiting_price, F.text)
    async def receive_price(
        message: Message, state: FSMContext, item_repo: IItemRepository
    ) -> None:
        assert message.text is not None
        data = await state.get_data()
        item_id = int(data["item_id"])
        try:
            response = await SetPriceUseCase(item_repo).execute(
                SetPriceRequest(item_id=item_id, price_text=message.text)
            )
        except DomainError as exc:
            await message.answer(f"That doesn't look like a price: {exc}\nTry again or /cancel.")
            return
        await state.clear()
        item = response.item
        await message.answer(format_item_card(item), reply_markup=item_keyboard(item, for_son=True))

    @router.callback_query(F.data.startswith("st:"), F.from_user.id == son_id)
    async def change_status(callback: CallbackQuery, item_repo: IItemRepository) -> None:
        assert callback.data is not None
        if not isinstance(callback.message, Message):
            await callback.answer("Message not available.", show_alert=True)
            return
        try:
            _, raw_id, raw_status = callback.data.split(":")
            request = ChangeStatusRequest(item_id=int(raw_id), target=ItemStatus(raw_status))
        except (ValueError, KeyError):
            await callback.answer("Bad button payload.", show_alert=True)
            return
        try:
            response = await ChangeStatusUseCase(item_repo).execute(request)
        except DomainError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        item = response.item
        await callback.message.edit_text(
            format_item_card(item), reply_markup=item_keyboard(item, for_son=True)
        )
        await callback.answer("Updated ✅")

    @router.callback_query(F.data.startswith("st:"))
    async def change_status_denied(callback: CallbackQuery) -> None:
        await callback.answer("Only son can change statuses 😉", show_alert=True)

    return router
