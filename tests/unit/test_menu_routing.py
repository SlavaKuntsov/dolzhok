"""Menu routing: main menu → «💰 Долги» submenu → actions → back.

Uses a fake Bot session so no network is touched: we only assert which reply
keyboard each entry point produces and that role gating holds.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

from src.adapters.telegram.keyboards import (
    BTN_BACK,
    BTN_DEBT,
    BTN_DEBTS,
    BTN_PAY,
    BTN_PAYMENTS,
)
from src.adapters.telegram.routers import build_root_router
from src.infrastructure.config import Settings
from tests.unit.fakes import InMemoryItemRepository, InMemoryRepaymentRepository

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


def _labels(session: _FakeSession) -> list[str]:
    markup = session.calls[-1].reply_markup
    return [b.text for row in markup.keyboard for b in row]


async def test_debt_submenu_flow() -> None:
    settings = _settings()
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["item_repo"] = InMemoryItemRepository()
    dispatcher["repayment_repo"] = InMemoryRepaymentRepository()
    dispatcher["app_settings"] = settings
    dispatcher.include_router(build_root_router(settings))

    bot = Bot(token=_TOKEN)
    session = _FakeSession(bot)
    bot.session = session  # type: ignore[assignment]

    try:
        # «💰 Долги» opens straight into the debt summary (like «💰 Долг»);
        # executor's submenu offers «Погасить», customer's does not.
        await _feed(dispatcher, bot, session, EXECUTOR_ID, BTN_DEBTS)
        assert _labels(session) == [BTN_DEBT, BTN_PAYMENTS, BTN_PAY, BTN_BACK]
        assert "Заказчик должен" in session.calls[-1].text

        await _feed(dispatcher, bot, session, CUSTOMER_ID, BTN_DEBTS)
        assert _labels(session) == [BTN_DEBT, BTN_PAYMENTS, BTN_BACK]
        assert "Заказчик должен" in session.calls[-1].text

        # «💰 Долг» keeps the user in the submenu.
        await _feed(dispatcher, bot, session, CUSTOMER_ID, BTN_DEBT)
        assert _labels(session) == [BTN_DEBT, BTN_PAYMENTS, BTN_BACK]
        assert "Заказчик должен" in session.calls[-1].text

        # «⬅️ Назад» returns to the main menu (no money buttons there).
        await _feed(dispatcher, bot, session, EXECUTOR_ID, BTN_BACK)
        assert _labels(session) == ["📋 Список", BTN_DEBTS, "📊 Статистика", "❌ Отмена"]
    finally:
        await session.close()
