"""Bot entrypoint: wire config -> db -> repo -> dispatcher -> long polling."""

from __future__ import annotations

import asyncio
import logging
import re
import sys

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from pydantic import ValidationError

from src.adapters.persistence.sqlite_repo import SqliteItemRepository
from src.adapters.telegram.routers import build_root_router
from src.infrastructure.config import get_settings
from src.infrastructure.db import create_engine, create_session_factory, init_db
from src.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"^\d+:[\w-]{30,}$")


def _check_token_format(token: str) -> None:
    """Fail fast on copy-paste mistakes (quotes, spaces, placeholder)."""
    if not _TOKEN_RE.match(token.strip()):
        print(
            "BOT_TOKEN doesn't look like a Telegram token "
            "(expected digits, colon, ~35 chars from @BotFather). "
            "Check .env for quotes, spaces, or the example placeholder.",
            file=sys.stderr,
        )
        raise SystemExit(2)


async def amain() -> None:
    try:
        settings = get_settings()
    except ValidationError as exc:
        print(
            "Invalid config: copy .env.example to .env and fill "
            f"BOT_TOKEN, DAD_ID, SON_ID.\nDetails: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    setup_logging(settings.log_level)
    _check_token_format(settings.bot_token)

    engine = create_engine(settings.database_url)
    await init_db(engine)

    repo = SqliteItemRepository(create_session_factory(engine))
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["item_repo"] = repo
    dispatcher["app_settings"] = settings
    dispatcher.include_router(build_root_router(settings))

    try:
        async with Bot(token=settings.bot_token.strip()) as bot:
            # Keep queued updates: Telegram stores them up to 24h,
            # we catch up after restarts.
            await bot.delete_webhook(drop_pending_updates=False)
            logger.info("bot started, polling")
            await dispatcher.start_polling(bot, allowed_updates=["message", "callback_query"])
    except TelegramUnauthorizedError:
        logger.error(
            "Telegram rejected BOT_TOKEN (Unauthorized). "
            "Regenerate it via @BotFather (/mybots -> API Token) and update .env."
        )
        raise SystemExit(2) from None
    except TelegramNetworkError as exc:
        logger.error("Cannot reach Telegram API (%s). Check network/VPN and retry.", exc)
        raise SystemExit(1) from None


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
