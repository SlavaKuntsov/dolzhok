"""0003 must advance the Postgres id sequence past the rows it copies.

DESTRUCTIVE: rewinds the schema to 0002 and back, so it runs only against a
scratch database and only when explicitly opted in:

    TEST_DATABASE_URL_RESET=postgresql://… uv run pytest \
        tests/integration/test_migration_0003_sequence.py
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import text

from alembic import command
from src.infrastructure.db import create_engine, normalize_database_url

URL = os.environ.get("TEST_DATABASE_URL_RESET")

pytestmark = pytest.mark.skipif(URL is None, reason="TEST_DATABASE_URL_RESET not set")

ROOT = Path(__file__).resolve().parents[2]
ACTOR = 7


def _config() -> Config:
    assert URL is not None
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    url = normalize_database_url(URL).render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def _insert_items(count: int) -> list[int]:
    async def run() -> list[int]:
        engine = create_engine(URL)  # type: ignore[arg-type]
        try:
            ids: list[int] = []
            async with engine.begin() as conn:
                for _ in range(count):
                    url = f"https://ozon.ru/product/{uuid.uuid4()}"
                    result = await conn.execute(
                        text(
                            "INSERT INTO items "
                            "(url, sku, title, price_kop, qty, status, payment, "
                            "created_by, created_at) "
                            "VALUES (:url, NULL, :title, 100, 1, 'NEW', NULL, "
                            ":actor, now()) RETURNING id"
                        ),
                        {"url": url, "title": url, "actor": ACTOR},
                    )
                    ids.append(result.scalar_one())
            return ids
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _delete_test_rows() -> None:
    async def run() -> None:
        engine = create_engine(URL)  # type: ignore[arg-type]
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("DELETE FROM items WHERE created_by = :actor"), {"actor": ACTOR}
                )
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_0003_advances_sequence_for_copied_rows() -> None:
    config = _config()
    command.upgrade(config, "head")
    command.downgrade(config, "0002_add_qty")
    try:
        copied = _insert_items(2)  # rows that 0003 copies with explicit ids
        command.upgrade(config, "head")
        fresh = _insert_items(1)  # would collide on a stale sequence
        assert fresh[0] > max(copied)
    finally:
        command.upgrade(config, "head")
        _delete_test_rows()
