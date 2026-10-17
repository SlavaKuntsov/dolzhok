"""FastAPI ASGI app serving the Telegram webhook (Vercel serverless).

Telegram POSTs each update to ``/webhook``; we hand it to the same aiogram
dispatcher used by long polling (see ``src/infrastructure/bootstrap.py``).
Resources are built once per warm instance in the lifespan; cold starts pay the
import + DB connect cost only.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from src.infrastructure.bootstrap import build_dispatcher
from src.infrastructure.config import Settings, get_settings
from src.infrastructure.db import create_engine, init_db
from src.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)

# Telegram echoes the secret token from setWebhook in this header.
SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


def build_webhook_router() -> APIRouter:
    """Routes that read the live bot/dispatcher/secret from ``app.state``."""
    router = APIRouter()

    @router.get("/")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    @router.post("/webhook")
    async def webhook(request: Request) -> Response:
        state = request.app.state
        secret: str | None = getattr(state, "webhook_secret", None)
        if secret is not None and request.headers.get(SECRET_HEADER) != secret:
            logger.warning("rejected webhook: bad secret token")
            return Response(status_code=403)
        bot: Bot = state.bot
        dispatcher: Dispatcher = state.dispatcher
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        return JSONResponse({"ok": True})

    return router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = getattr(app.state, "settings", None) or get_settings()
    setup_logging(settings.log_level)

    engine = create_engine(settings.database_url)
    await init_db(engine)
    dispatcher = build_dispatcher(settings, engine)
    bot = Bot(token=settings.bot_token.strip())

    if not settings.webhook_secret:
        logger.warning(
            "WEBHOOK_SECRET is not set: /webhook accepts any POST. Set a secret "
            "in production so Telegram's header can be verified."
        )

    app.state.settings = settings
    app.state.engine = engine
    app.state.bot = bot
    app.state.dispatcher = dispatcher
    app.state.webhook_secret = settings.webhook_secret
    try:
        yield
    finally:
        await bot.session.close()
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI app. ``settings`` defaults to env at lifespan start."""
    app = FastAPI(lifespan=_lifespan)
    if settings is not None:
        app.state.settings = settings
    app.include_router(build_webhook_router())
    return app


app = create_app()
