"""Item flow: ingest Ozon links, price FSM, status buttons (son only)."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.adapters.telegram.cards import format_item_card
from src.adapters.telegram.fsm import PriceStates
from src.adapters.telegram.keyboards import item_keyboard, main_menu_keyboard
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
    dad_id = settings.dad_id

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
                await message.answer(
                    "Я отслеживаю только ссылки Ozon (ozon.ru / ozo.ru) 🔗",
                    reply_markup=main_menu_keyboard(),
                )
            return
        sender_id = message.from_user.id
        raw_url = urls[0]
        try:
            response = await AddItemUseCase(item_repo, url_resolver).execute(
                AddItemRequest(
                    raw_url=raw_url,
                    from_user_id=sender_id,
                    title=ozon.extract_title(message.text, raw_url),
                )
            )
        except DomainError as exc:
            await message.answer(f"Не получилось сохранить ссылку: {exc}")
            return
        item = response.item
        is_son = sender_id == son_id
        header = "✅ Сохранено" if response.created else "ℹ️ Уже отслеживаю"
        await message.answer(
            f"{header} #{item.id}\n\n{format_item_card(item)}",
            reply_markup=item_keyboard(item, for_son=is_son),
            disable_web_page_preview=True,
        )
        # Notify the other party so both chats stay in sync.
        other_id = dad_id if is_son else son_id
        who = "Сын добавил" if is_son else "Папа прислал"
        await bot.send_message(
            other_id,
            f"🆕 {who} #{item.id}\n\n{format_item_card(item)}",
            reply_markup=item_keyboard(item, for_son=not is_son),
            disable_web_page_preview=True,
        )

    @router.callback_query(F.data.startswith("price:"), F.from_user.id == son_id)
    async def ask_price(
        callback: CallbackQuery, state: FSMContext, item_repo: IItemRepository
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
        if item is None or item.is_closed:
            await callback.answer("Товар недоступен.", show_alert=True)
            return
        await state.set_state(PriceStates.waiting_price)
        await state.update_data(item_id=item_id)
        await callback.message.answer(
            f"Введи цену для #{item_id} (например, 1 299,50). /cancel — отмена."
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("price:"))
    async def ask_price_denied(callback: CallbackQuery) -> None:
        await callback.answer("Цены ставит только сын 😉", show_alert=True)

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
            await message.answer(f"Не похоже на цену: {exc}\nПопробуй еще раз или /cancel.")
            return
        await state.clear()
        item = response.item
        await message.answer(
            format_item_card(item),
            reply_markup=item_keyboard(item, for_son=True),
            disable_web_page_preview=True,
        )

    @router.callback_query(F.data.startswith("st:"), F.from_user.id == son_id)
    async def change_status(callback: CallbackQuery, item_repo: IItemRepository) -> None:
        assert callback.data is not None
        if not isinstance(callback.message, Message):
            await callback.answer("Сообщение недоступно.", show_alert=True)
            return
        try:
            _, raw_id, raw_status = callback.data.split(":")
            request = ChangeStatusRequest(item_id=int(raw_id), target=ItemStatus(raw_status))
        except (ValueError, KeyError):
            await callback.answer("Битые данные кнопки.", show_alert=True)
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
        await callback.answer("Готово ✅")

    @router.callback_query(F.data.startswith("st:"))
    async def change_status_denied(callback: CallbackQuery) -> None:
        await callback.answer("Статусы меняет только сын 😉", show_alert=True)

    return router
