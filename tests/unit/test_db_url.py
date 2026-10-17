"""Postgres URL normalization (driver + Neon params → asyncpg)."""

from __future__ import annotations

from src.infrastructure.db import normalize_database_url


def test_bare_postgresql_gets_asyncpg_driver() -> None:
    url = normalize_database_url("postgresql://u:p@h/db")
    assert url.drivername == "postgresql+asyncpg"


def test_neon_params_translated_for_asyncpg() -> None:
    url = normalize_database_url(
        "postgresql+asyncpg://u:p@ep-x.neon.tech/db?sslmode=require&channel_binding=require"
    )
    assert url.get_backend_name() == "postgresql"
    assert dict(url.query) == {"ssl": "require"}


def test_bare_neon_url_driver_and_params() -> None:
    url = normalize_database_url(
        "postgresql://u:p@ep-x-pooler.neon.tech/db?channel_binding=require&sslmode=require"
    )
    assert url.drivername == "postgresql+asyncpg"
    assert dict(url.query) == {"ssl": "require"}


def test_asyncpg_url_without_ssl_params_untouched() -> None:
    url = normalize_database_url("postgresql+asyncpg://u:p@h/db")
    assert dict(url.query) == {}


def test_existing_ssl_param_wins_over_sslmode() -> None:
    url = normalize_database_url("postgresql+asyncpg://u:p@h/db?sslmode=require&ssl=verify-full")
    assert dict(url.query) == {"ssl": "verify-full"}


def test_explicit_non_asyncpg_driver_untouched() -> None:
    url = normalize_database_url("postgresql+psycopg2://u:p@h/db")
    assert url.drivername == "postgresql+psycopg2"


def test_sqlite_url_passthrough() -> None:
    url = normalize_database_url("sqlite+aiosqlite:///./data/bot.db")
    assert url.get_backend_name() == "sqlite"
