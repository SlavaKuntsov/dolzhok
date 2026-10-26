"""Item flow: ingest Ozon links, price FSM, status buttons (executor only)."""

from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.adapters.telegram.cards import card_message
from src.adapters.telegram.fsm import (
    ManualDebtStates,
    PriceStates,
    QtyStates,
    RepaymentStates,
)
from src.adapters.telegram.keyboards import main_menu_keyboard
from src.domain import ozon
from src.domain.entities import ItemStatus, PaymentType
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository
from src.domain.value_objects import parse_price_to_kop
from src.infrastructure.config import Settings
from src.use_cases.add_item import AddItemRequest, AddItemUseCase
from src.use_cases.change_status import ChangeStatusRequest, ChangeStatusUseCase
from src.use_cases.set_payment import SetPaymentRequest, SetPaymentUseCase
from src.use_cases.set_price import SetPriceRequest, SetPriceUseCase
from src.use_cases.set_quantity import SetQuantityRequest, SetQuantityUseCase

logger = logging.getLogger(__name__)

_CARD_ID_RE = re.compile(r"#(\d+)")


def parse_reply_price(text: str, replied_text: str | None) -> tuple[int, int] | None:
    """Stateless price set: reply to a card with a price. Returns (item_id, kop)."""
    if not replied_text:
        return None
    match = _CARD_ID_RE.search(replied_text)
    if not match:
        return None
    try:
        return int(match.group(1)), parse_price_to_kop(text)
    except DomainError:
        return None


def build_items_router(settings: Settings) -> Router:
    router = Router(name="items")
    executor_id = settings.executor_id

    # NOTE: registered before ingest_link, but ingest_link also excludes
    # waiting states via StateFilter — belt and suspenders against shadowing.
    @router.message(F.text, F.reply_to_message)
    async def price_by_reply(message: Message, item_repo: IItemRepository) -> None:
        """Set price by replying to a card. Stateless: survives bot restarts."""
        assert message.text is not None
        replied = message.reply_to_message
        parsed = parse_reply_price(message.text, replied.text if replied is not None else None)
        if parsed is None:
            raise SkipHandler
        item_id, price_kop = parsed
        try:
            response = await SetPriceUseCase(item_repo).execute(
                SetPriceRequest(item_id=item_id, price_kop=price_kop)
            )
        except DomainError as exc:
            await message.answer(f"Не получилось: {exc}")
            return
        item = response.item
        await message.answer(**card_message(item, for_executor=True))

    @router.message(
        F.text,
        ~StateFilter(
            PriceStates.waiting_price,
            QtyStates.waiting_qty,
            ManualDebtStates.waiting_amount,
            ManualDebtStates.waiting_total,
            RepaymentStates.waiting_amount,
            RepaymentStates.waiting_note,
        ),
    )
    async def ingest_link(
        message: Message,
        bot: Bot,
        item_repo: IItemRepository,
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
            else:
                try:
                    parse_price_to_kop(message.text)
                except DomainError:
                    return
                await message.answer(
                    "Похоже на цену 🙂 Нажми ✏️ Цена на карточке товара "
                    "или просто ответь на карточку ценой — так надежнее.",
                    reply_markup=main_menu_keyboard(),
                )
            return
        sender_id = message.from_user.id
        raw_url = urls[0]
        try:
            response = await AddItemUseCase(item_repo).execute(
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
        is_executor = sender_id == executor_id
        await message.answer(
            **card_message(item, for_executor=is_executor, prefix=f"✅ Сохранено #{item.id}")
        )
        if is_executor:
            # The executor's own additions never ping the customer: they only see
            # their own chat, so links added here stay invisible to them.
            return
        # Mirror the customer's link into the executor's chat.
        try:
            await bot.send_message(
                executor_id,
                **card_message(item, for_executor=True, prefix=f"🆕 Заказчик прислал #{item.id}"),
            )
        except TelegramBadRequest:
            # No chat yet: the executor never pressed /start.
            logger.warning("notify copy to %s failed: chat not found", executor_id)
            await message.answer(
                "⚠️ Вторая сторона еще не запустила бота (/start) — копия не доставлена."
            )

    @router.callback_query(F.data.startswith("price:"), F.from_user.id == executor_id)
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
        await callback.answer("Цены ставит только исполнитель 😉", show_alert=True)

    @router.callback_query(F.data.startswith("qty:"), F.from_user.id == executor_id)
    async def ask_qty(
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
        await state.set_state(QtyStates.waiting_qty)
        await state.update_data(item_id=item_id)
        await callback.message.answer(
            f"Введи количество для #{item_id} (например, 2). /cancel — отмена."
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("qty:"))
    async def ask_qty_denied(callback: CallbackQuery) -> None:
        await callback.answer("Количество меняет только исполнитель 😉", show_alert=True)

    @router.message(QtyStates.waiting_qty, F.text)
    async def receive_qty(message: Message, state: FSMContext, item_repo: IItemRepository) -> None:
        assert message.text is not None
        data = await state.get_data()
        item_id = int(data["item_id"])
        try:
            response = await SetQuantityUseCase(item_repo).execute(
                SetQuantityRequest(item_id=item_id, qty_text=message.text)
            )
        except DomainError as exc:
            await message.answer(f"Не похоже на количество: {exc}\nПопробуй еще раз или /cancel.")
            return
        await state.clear()
        item = response.item
        await message.answer(**card_message(item, for_executor=True))

    @router.message(PriceStates.waiting_price, F.text)
    async def receive_price(
        message: Message, state: FSMContext, item_repo: IItemRepository
    ) -> None:
        assert message.text is not None
        data = await state.get_data()
        item_id = int(data["item_id"])
        try:
            price_kop = parse_price_to_kop(message.text)
        except DomainError as exc:
            await message.answer(f"Не похоже на цену: {exc}\nПопробуй еще раз или /cancel.")
            return
        try:
            response = await SetPriceUseCase(item_repo).execute(
                SetPriceRequest(item_id=item_id, price_kop=price_kop)
            )
        except DomainError as exc:
            await state.clear()
            await message.answer(f"Не получилось: {exc}")
            return
        await state.clear()
        item = response.item
        await message.answer(**card_message(item, for_executor=True))

    @router.callback_query(F.data.startswith("st:"), F.from_user.id == executor_id)
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
        await callback.message.edit_text(**card_message(item, for_executor=True))
        await callback.answer("Готово ✅")

    @router.callback_query(F.data.startswith("st:"))
    async def change_status_denied(callback: CallbackQuery) -> None:
        await callback.answer("Статусы меняет только исполнитель 😉", show_alert=True)

    @router.callback_query(F.data.startswith("pay:"), F.from_user.id == executor_id)
    async def change_payment(callback: CallbackQuery, item_repo: IItemRepository) -> None:
        assert callback.data is not None
        if not isinstance(callback.message, Message):
            await callback.answer("Сообщение недоступно.", show_alert=True)
            return
        try:
            _, raw_id, raw_payment = callback.data.split(":")
            request = SetPaymentRequest(item_id=int(raw_id), payment=PaymentType(raw_payment))
        except (ValueError, KeyError):
            await callback.answer("Битые данные кнопки.", show_alert=True)
            return
        try:
            response = await SetPaymentUseCase(item_repo).execute(request)
        except DomainError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        item = response.item
        await callback.message.edit_text(**card_message(item, for_executor=True))
        await callback.answer("Оплата сохранена ✅")

    @router.callback_query(F.data.startswith("pay:"))
    async def change_payment_denied(callback: CallbackQuery) -> None:
        await callback.answer("Оплату отмечает только исполнитель 😉", show_alert=True)

    @router.callback_query(F.data.startswith("noop:"))
    async def noop(callback: CallbackQuery) -> None:
        await callback.answer("Уже в этом статусе")

    return router
