"""Webhook settings: public URL composition."""

from __future__ import annotations

from src.infrastructure.config import Settings


def _settings(**kwargs: object) -> Settings:
    base: dict[str, object] = {
        "bot_token": "123456789:" + "A" * 35,
        "customer_id": 1,
        "executor_id": 2,
    }
    base.update(kwargs)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_webhook_url_composed_from_base() -> None:
    settings = _settings(webhook_base_url="https://dolzhok.vercel.app/")
    assert settings.webhook_url == "https://dolzhok.vercel.app/webhook"


def test_webhook_url_custom_path() -> None:
    settings = _settings(webhook_base_url="https://dolzhok.vercel.app", webhook_path="hook")
    assert settings.webhook_url == "https://dolzhok.vercel.app/hook"


def test_webhook_url_none_without_base() -> None:
    assert _settings().webhook_url is None
