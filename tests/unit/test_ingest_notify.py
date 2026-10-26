"""Ingest-link notification rules: executor adds silently, customer mirrors.

Uses a fake Bot session so no network is touched. The rule under test: when the
executor sends a link, nothing is sent to the customer; when the customer sends
one, it is mirrored into the executor's chat.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

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
OZON_LINK = "https://www.ozon.ru/product/phone-123456789/"


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


def _build() -> tuple[Dispatcher, Bot, _FakeSession]:
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
    return dispatcher, bot, session


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


async def test_executor_link_sends_nothing_to_customer() -> None:
    dispatcher, bot, session = _build()
    try:
        await _feed(dispatcher, bot, session, EXECUTOR_ID, OZON_LINK)

        send_chat_ids = [m.chat_id for m in session.calls if type(m).__name__ == "SendMessage"]
        assert send_chat_ids == [EXECUTOR_ID]
        assert CUSTOMER_ID not in send_chat_ids
    finally:
        await session.close()


async def test_customer_link_is_mirrored_to_executor() -> None:
    dispatcher, bot, session = _build()
    try:
        await _feed(dispatcher, bot, session, CUSTOMER_ID, OZON_LINK)

        sends = [m for m in session.calls if type(m).__name__ == "SendMessage"]
        assert [m.chat_id for m in sends] == [CUSTOMER_ID, EXECUTOR_ID]
        assert "Заказчик прислал" in sends[-1].text
    finally:
        await session.close()
