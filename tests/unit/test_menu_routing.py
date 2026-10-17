"""Menu routing: main menu → «💰 Долги» submenu → actions → back.

Uses a fake Bot session so no network is touched: we only assert which reply
keyboard each entry point produces and that role gating holds.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from src.adapters.telegram.keyboards import (
    BTN_BACK,
    BTN_DEBT,
    BTN_DEBTS,
    BTN_MANUAL_ADD,
    BTN_MANUAL_EDIT,
    BTN_MANUAL_RESET,
    BTN_PAY,
    BTN_PAYMENTS,
)
from src.adapters.telegram.routers import build_root_router
from src.infrastructure.config import Settings
from tests.unit.fakes import (
    InMemoryItemRepository,
    InMemoryManualDebtRepository,
    InMemoryRepaymentRepository,
)

EXECUTOR_ID = 22
CUSTOMER_ID = 11
_TOKEN = "123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class _FakeSession:
    """Captures outgoing Bot API methods and returns canned responses."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.calls: list[Any] = []

    async def __call__(self, bot: Bot, method: Any, timeout: float | None = None) -> Any:
        self.calls.append(method)
        if type(method).__name__ == "SendMessage":
            return Message(
                message_id=len(self.calls),
                date=datetime.now(UTC),
                chat=Chat(id=method.chat_id, type="private"),
                text=method.text,
                from_user=User(id=0, is_bot=True, first_name="bot"),
            )
        return True

    async def close(self) -> None:
        pass


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        bot_token=_TOKEN,
        customer_id=CUSTOMER_ID,
        executor_id=EXECUTOR_ID,
        _env_file=None,
    )


async def _feed(
    dispatcher: Dispatcher, bot: Bot, session: _FakeSession, uid: int, text: str
) -> None:
    update = Update(
        update_id=len(session.calls) + 1,
        message=Message(
            message_id=len(session.calls) + 1,
            date=datetime.now(UTC),
            chat=Chat(id=uid, type="private"),
            from_user=User(id=uid, is_bot=False, first_name="u"),
            text=text,
        ),
    )
    await dispatcher.feed_update(bot, update)


async def _feed_callback(
    dispatcher: Dispatcher, bot: Bot, session: _FakeSession, uid: int, data: str
) -> None:
    update = Update(
        update_id=len(session.calls) + 1,
        callback_query=CallbackQuery(
            id=str(len(session.calls) + 1),
            from_user=User(id=uid, is_bot=False, first_name="u"),
            chat_instance="chat-instance",
            data=data,
            message=Message(
                message_id=len(session.calls) + 1,
                date=datetime.now(UTC),
                chat=Chat(id=uid, type="private"),
                text="debt",
            ),
        ),
    )
    await dispatcher.feed_update(bot, update)


def _labels(session: _FakeSession) -> list[str]:
    markup = session.calls[-1].reply_markup
    return [b.text for row in markup.keyboard for b in row]


async def test_debt_submenu_flow() -> None:
    settings = _settings()
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["item_repo"] = InMemoryItemRepository()
    dispatcher["repayment_repo"] = InMemoryRepaymentRepository()
    dispatcher["manual_debt_repo"] = InMemoryManualDebtRepository()
    dispatcher["app_settings"] = settings
    dispatcher.include_router(build_root_router(settings))

    bot = Bot(token=_TOKEN)
    session = _FakeSession(bot)
    bot.session = session  # type: ignore[assignment]

    try:
        # «💰 Долги» opens straight into the debt summary (like «💰 Долг»);
        # executor's submenu offers «Погасить», customer's does not.
        await _feed(dispatcher, bot, session, EXECUTOR_ID, BTN_DEBTS)
        assert _labels(session) == [
            BTN_DEBT,
            BTN_PAYMENTS,
            BTN_MANUAL_ADD,
            BTN_PAY,
            BTN_MANUAL_EDIT,
            BTN_MANUAL_RESET,
            BTN_BACK,
        ]
        assert "Долг по товарам" in session.calls[-1].text
        assert "Долги за прошлое" in session.calls[-1].text

        await _feed(dispatcher, bot, session, CUSTOMER_ID, BTN_DEBTS)
        assert _labels(session) == [BTN_DEBT, BTN_PAYMENTS, BTN_BACK]
        assert "💰 Долг: 0,00 BYN" in session.calls[-1].text
        assert "Долг по товарам" not in session.calls[-1].text

        # «💰 Долг» keeps the user in the submenu.
        await _feed(dispatcher, bot, session, CUSTOMER_ID, BTN_DEBT)
        assert _labels(session) == [BTN_DEBT, BTN_PAYMENTS, BTN_BACK]
        assert "💰 Долг: 0,00 BYN" in session.calls[-1].text

        # «⬅️ Назад» returns to the main menu (no money buttons there).
        await _feed(dispatcher, bot, session, EXECUTOR_ID, BTN_BACK)
        assert _labels(session) == ["📋 Список", BTN_DEBTS, "📊 Статистика", "❌ Отмена"]
    finally:
        await session.close()


async def test_manual_debt_add_flow_executor_only() -> None:
    settings = _settings()
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["item_repo"] = InMemoryItemRepository()
    dispatcher["repayment_repo"] = InMemoryRepaymentRepository()
    manual = InMemoryManualDebtRepository()
    dispatcher["manual_debt_repo"] = manual
    dispatcher["app_settings"] = settings
    dispatcher.include_router(build_root_router(settings))

    bot = Bot(token=_TOKEN)
    session = _FakeSession(bot)
    bot.session = session  # type: ignore[assignment]

    try:
        # Customer cannot arm the manual-debt flow.
        await _feed(dispatcher, bot, session, CUSTOMER_ID, BTN_MANUAL_ADD)
        assert "только исполнитель" in session.calls[-1].text
        assert (await manual.get()).amount_kop == 0

        # Executor adds 500,00, then subtracts 200,00.
        await _feed(dispatcher, bot, session, EXECUTOR_ID, BTN_MANUAL_ADD)
        await _feed(dispatcher, bot, session, EXECUTOR_ID, "500")
        assert (await manual.get()).amount_kop == 50000
        assert "Долги за прошлое: 500,00 BYN" in session.calls[-1].text

        await _feed(dispatcher, bot, session, EXECUTOR_ID, BTN_MANUAL_ADD)
        await _feed(dispatcher, bot, session, EXECUTOR_ID, "-200")
        assert (await manual.get()).amount_kop == 30000
        assert "Долги за прошлое: 300,00 BYN" in session.calls[-1].text
    finally:
        await session.close()


async def test_manual_debt_reset_requires_confirmation() -> None:
    settings = _settings()
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["item_repo"] = InMemoryItemRepository()
    dispatcher["repayment_repo"] = InMemoryRepaymentRepository()
    manual = InMemoryManualDebtRepository(amount_kop=50000)
    dispatcher["manual_debt_repo"] = manual
    dispatcher["app_settings"] = settings
    dispatcher.include_router(build_root_router(settings))

    bot = Bot(token=_TOKEN)
    session = _FakeSession(bot)
    bot.session = session  # type: ignore[assignment]

    try:
        # Cancel keeps the figure untouched.
        await _feed_callback(dispatcher, bot, session, EXECUTOR_ID, "mdreset:no")
        assert (await manual.get()).amount_kop == 50000

        # Customer cannot reset.
        await _feed_callback(dispatcher, bot, session, CUSTOMER_ID, "mdreset:ok")
        assert (await manual.get()).amount_kop == 50000
        assert session.calls[-1].text == "Сбрасывать долг может только исполнитель 😉"

        # Executor confirms: figure becomes zero.
        await _feed_callback(dispatcher, bot, session, EXECUTOR_ID, "mdreset:ok")
        assert (await manual.get()).amount_kop == 0
    finally:
        await session.close()


async def test_manual_debt_zero_delta_is_rejected() -> None:
    settings = _settings()
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["item_repo"] = InMemoryItemRepository()
    dispatcher["repayment_repo"] = InMemoryRepaymentRepository()
    manual = InMemoryManualDebtRepository()
    dispatcher["manual_debt_repo"] = manual
    dispatcher["app_settings"] = settings
    dispatcher.include_router(build_root_router(settings))

    bot = Bot(token=_TOKEN)
    session = _FakeSession(bot)
    bot.session = session  # type: ignore[assignment]

    try:
        await _feed(dispatcher, bot, session, EXECUTOR_ID, BTN_MANUAL_ADD)
        await _feed(dispatcher, bot, session, EXECUTOR_ID, "0")
        assert (await manual.get()).amount_kop == 0
        assert "не может быть нулевой" in session.calls[-1].text
    finally:
        await session.close()
