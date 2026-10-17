"""Postgres/asyncpg URL normalization (Neon params → asyncpg)."""

from __future__ import annotations

from src.infrastructure.db import _normalize_url


def test_neon_params_translated_for_asyncpg() -> None:
    url = _normalize_url(
        "postgresql+asyncpg://u:p@ep-x.neon.tech/db?sslmode=require&channel_binding=require"
    )
    assert url.get_backend_name() == "postgresql"
    assert dict(url.query) == {"ssl": "require"}


def test_asyncpg_url_without_ssl_params_untouched() -> None:
    url = _normalize_url("postgresql+asyncpg://u:p@h/db")
    assert dict(url.query) == {}


def test_existing_ssl_param_wins_over_sslmode() -> None:
    url = _normalize_url("postgresql+asyncpg://u:p@h/db?sslmode=require&ssl=verify-full")
    assert dict(url.query) == {"ssl": "verify-full"}


def test_sqlite_url_passthrough() -> None:
    url = _normalize_url("sqlite+aiosqlite:///./data/bot.db")
    assert url.get_backend_name() == "sqlite"
