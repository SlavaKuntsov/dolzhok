"""Router assembly with whitelist applied to every update."""

from __future__ import annotations

from aiogram import Router

from src.adapters.telegram.middleware import WhitelistMiddleware
from src.adapters.telegram.routers.items import build_items_router
from src.adapters.telegram.routers.start import build_start_router
from src.infrastructure.config import Settings


def build_root_router(settings: Settings) -> Router:
    root = Router(name="root")
    whitelist = WhitelistMiddleware(settings.allowed_user_ids)
    root.message.middleware(whitelist)
    root.callback_query.middleware(whitelist)
    root.include_router(build_start_router(settings))
    root.include_router(build_items_router(settings))
    return root
