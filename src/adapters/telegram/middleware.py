"""Whitelist middleware: ignore updates from strangers, no reply (anti-spam)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class WhitelistMiddleware(BaseMiddleware):
    """Drop updates from users outside the whitelist."""

    def __init__(self, allowed_user_ids: frozenset[int]) -> None:
        self._allowed = allowed_user_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        user_id = getattr(user, "id", None)
        if user_id not in self._allowed:
            logger.warning("ignored update from unknown user_id=%s", user_id)
            return None
        return await handler(event, data)
