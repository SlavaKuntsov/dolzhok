"""Postgres engines must not keep a client-side pool (serverless + Neon pooler)."""

from __future__ import annotations

from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from src.infrastructure.db import create_engine


def test_postgres_uses_null_pool() -> None:
    engine = create_engine("postgresql://u:p@ep-x-pooler.neon.tech/db?sslmode=require")
    try:
        assert isinstance(engine.pool, NullPool)
    finally:
        # No connections were opened; dispose is a no-op awaitable.
        engine.sync_engine.dispose()


def test_sqlite_keeps_default_pool() -> None:
    engine = create_engine("sqlite+aiosqlite:///./data/test-pool.db")
    try:
        assert isinstance(engine.pool, AsyncAdaptedQueuePool)
    finally:
        engine.sync_engine.dispose()
