"""Webhook ASGI router: auth by secret token + update hand-off."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.adapters.webhook.app import SECRET_HEADER, build_webhook_router

TOKEN = "123456789:" + "A" * 35

_UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "date": 1_700_000_000,
        "chat": {"id": 42, "type": "private"},
        "from": {"id": 42, "is_bot": False, "first_name": "T"},
        "text": "/start",
    },
}


class _FakeDispatcher:
    def __init__(self) -> None:
        self.updates: list[Update] = []

    async def feed_update(self, bot: Bot, update: Update) -> None:
        self.updates.append(update)


def _app(dispatcher: _FakeDispatcher, secret: str | None) -> FastAPI:
    app = FastAPI()
    app.state.bot = Bot(token=TOKEN)
    app.state.dispatcher = dispatcher
    app.state.webhook_secret = secret
    app.include_router(build_webhook_router())
    return app


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_health() -> None:
    async with _client(_app(_FakeDispatcher(), None)) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_webhook_feeds_update() -> None:
    dispatcher = _FakeDispatcher()
    async with _client(_app(dispatcher, None)) as client:
        resp = await client.post("/webhook", json=_UPDATE)
    assert resp.status_code == 200
    assert [u.update_id for u in dispatcher.updates] == [1]


async def test_webhook_rejects_bad_secret() -> None:
    dispatcher = _FakeDispatcher()
    async with _client(_app(dispatcher, "s3cret")) as client:
        resp = await client.post("/webhook", json=_UPDATE, headers={SECRET_HEADER: "nope"})
    assert resp.status_code == 403
    assert dispatcher.updates == []


async def test_webhook_accepts_when_secret_is_empty() -> None:
    # Empty env var means "not configured": the endpoint must stay open, same
    # as the startup warning says.
    dispatcher = _FakeDispatcher()
    async with _client(_app(dispatcher, "")) as client:
        resp = await client.post("/webhook", json=_UPDATE)
    assert resp.status_code == 200
    assert len(dispatcher.updates) == 1


async def test_webhook_accepts_whitespace_secret() -> None:
    # `WEBHOOK_SECRET=' '` is a misconfiguration, not a secret nobody can send.
    dispatcher = _FakeDispatcher()
    async with _client(_app(dispatcher, "   ")) as client:
        resp = await client.post("/webhook", json=_UPDATE)
    assert resp.status_code == 200
    assert len(dispatcher.updates) == 1


async def test_webhook_accepts_good_secret() -> None:
    dispatcher = _FakeDispatcher()
    async with _client(_app(dispatcher, "s3cret")) as client:
        resp = await client.post("/webhook", json=_UPDATE, headers={SECRET_HEADER: "s3cret"})
    assert resp.status_code == 200
    assert len(dispatcher.updates) == 1
