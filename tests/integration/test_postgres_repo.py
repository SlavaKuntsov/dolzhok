"""Postgres drift guard: Alembic migrations + repository roundtrip on Postgres.

Opt-in via ``TEST_DATABASE_URL`` (e.g. a throwaway Neon branch) so a machine
without Postgres stays green. Guards the ADR-0001 promise that schema and
repositories behave identically on SQLite and Postgres:

    TEST_DATABASE_URL='postgresql+asyncpg://...' uv run pytest tests/integration
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alembic import command
from src.adapters.persistence.repayment_repo import SqlAlchemyRepaymentRepository
from src.adapters.persistence.sqlalchemy_repo import SqlAlchemyItemRepository
from src.domain.entities import Item, ItemStatus, Repayment
from src.infrastructure.db import create_engine, normalize_database_url

URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(URL is None, reason="TEST_DATABASE_URL not set")

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def _migrated() -> Iterator[None]:
    assert URL is not None
    normalized = normalize_database_url(URL).render_as_string(hide_password=False)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = normalized
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", normalized)
    command.upgrade(config, "head")
    yield
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous


async def test_postgres_item_roundtrip() -> None:
    assert URL is not None
    engine = create_engine(URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    repo = SqlAlchemyItemRepository(factory)

    url = f"https://ozon.ru/product/{uuid.uuid4().hex}"
    saved = await repo.add(Item(url=url, created_by=7))
    assert saved.id is not None

    fetched = await repo.get_by_id(saved.id)
    assert fetched is not None and fetched.created_by == 7
    fetched.transition(ItemStatus.ORDERED)
    fetched.set_price(50000)
    updated = await repo.update(fetched)
    assert updated.status == ItemStatus.ORDERED
    assert updated.price_kop == 50000

    await engine.dispose()


async def test_postgres_repayment_roundtrip() -> None:
    assert URL is not None
    engine = create_engine(URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    repo = SqlAlchemyRepaymentRepository(factory)

    saved = await repo.add(Repayment(amount_kop=100000, created_by=7, note="neon"))
    assert saved.id is not None
    assert await repo.delete(saved.id) is True
    assert await repo.delete(saved.id) is False

    await engine.dispose()
