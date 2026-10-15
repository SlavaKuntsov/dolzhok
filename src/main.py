"""Bot entrypoint: wire config -> db -> repo -> dispatcher -> long polling."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.adapters.persistence.sqlite_repo import SqliteItemRepository
from src.adapters.telegram.routers import build_root_router
from src.adapters.url_resolver import HttpxOzonResolver
from src.infrastructure.config import get_settings
from src.infrastructure.db import create_engine, create_session_factory, init_db
from src.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)


async def amain() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    engine = create_engine(settings.database_url)
    await init_db(engine)

    repo = SqliteItemRepository(create_session_factory(engine))
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["item_repo"] = repo
    dispatcher["url_resolver"] = HttpxOzonResolver()
    dispatcher["app_settings"] = settings
    dispatcher.include_router(build_root_router(settings))

    bot = Bot(token=settings.bot_token)
    # Keep queued updates: Telegram stores them up to 24h, we catch up after restarts.
    await bot.delete_webhook(drop_pending_updates=False)
    logger.info("bot started, polling")
    await dispatcher.start_polling(bot, allowed_updates=["message", "callback_query"])


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
