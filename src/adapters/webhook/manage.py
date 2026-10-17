"""Register/unregister the Telegram webhook: ``python -m src.adapters.webhook.manage``.

set     -> setWebhook to WEBHOOK_BASE_URL (+ WEBHOOK_SECRET), run on deploy
delete  -> deleteWebhook, run on teardown / when switching back to polling
info    -> getWebhookInfo, to eyeball the current registration
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from aiogram import Bot

from src.infrastructure.config import Settings, get_settings
from src.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)

ALLOWED_UPDATES = ["message", "callback_query"]


async def _set(bot: Bot, settings: Settings) -> None:
    url = settings.webhook_url
    if url is None:
        logger.error("WEBHOOK_BASE_URL is not set; cannot register a webhook.")
        raise SystemExit(2)
    await bot.set_webhook(
        url=url,
        secret_token=settings.webhook_secret,
        allowed_updates=ALLOWED_UPDATES,
        drop_pending_updates=False,
    )
    logger.info("webhook set: url=%s secret=%s", url, "yes" if settings.webhook_secret else "no")


async def _delete(bot: Bot) -> None:
    # Keep queued updates: Telegram stores them, polling picks them up.
    await bot.delete_webhook(drop_pending_updates=False)
    logger.info("webhook deleted")


async def _info(bot: Bot) -> None:
    info = await bot.get_webhook_info()
    logger.info(
        "webhook info: url=%r pending=%d last_error=%r",
        info.url,
        info.pending_update_count,
        info.last_error_message,
    )


async def _run(action: str) -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    async with Bot(token=settings.bot_token.strip()) as bot:
        if action == "set":
            await _set(bot, settings)
        elif action == "delete":
            await _delete(bot)
        elif action == "info":
            await _info(bot)
        else:  # pragma: no cover - argparse restricts choices
            raise SystemExit(f"unknown action: {action}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the Telegram webhook.")
    parser.add_argument("action", choices=["set", "delete", "info"])
    args = parser.parse_args()
    asyncio.run(_run(args.action))


if __name__ == "__main__":
    main()
