"""SQLite repository roundtrip against a temp file (no network)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.adapters.persistence.models import Base
from src.adapters.persistence.sqlalchemy_repo import SqlAlchemyItemRepository
from src.domain.entities import Item, ItemStatus


async def _make_repo(tmp_path: Path) -> SqlAlchemyItemRepository:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/t.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return SqlAlchemyItemRepository(factory)


async def test_sqlite_roundtrip(tmp_path: Path) -> None:
    repo = await _make_repo(tmp_path)
    saved = await repo.add(Item(url="https://ozon.ru/product/x-1", created_by=7))
    assert saved.id is not None

    assert await repo.find_by_url("https://ozon.ru/product/x-1") is not None
    assert await repo.find_by_url("https://ozon.ru/other") is None

    fetched = await repo.get_by_id(saved.id)
    assert fetched is not None and fetched.created_by == 7

    fetched.transition(ItemStatus.ORDERED)
    fetched.set_price(50000)
    updated = await repo.update(fetched)
    assert updated.status == ItemStatus.ORDERED
    assert updated.price_kop == 50000

    recent = await repo.list_recent(limit=10)
    assert len(recent) == 1
    assert len(await repo.list_all()) == 1
