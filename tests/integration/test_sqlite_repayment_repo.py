"""SQLAlchemy repayment repository roundtrip against a temp SQLite file."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.adapters.persistence.models import Base
from src.adapters.persistence.repayment_repo import SqlAlchemyRepaymentRepository
from src.domain.entities import Repayment


async def test_repayment_repo_roundtrip(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/r.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    repo = SqlAlchemyRepaymentRepository(factory)

    saved = await repo.add(Repayment(amount_kop=100000, created_by=7, note="за сентябрь"))
    assert saved.id is not None

    first = [r for r in await repo.list_all() if r.id == saved.id][0]
    assert first.amount_kop == 100000
    assert first.note == "за сентябрь"
    assert first.created_by == 7

    await repo.add(Repayment(amount_kop=50000, created_by=7))
    listed = await repo.list_all()
    assert [r.amount_kop for r in listed] == [50000, 100000]  # newest first

    assert await repo.delete(saved.id) is True
    assert await repo.delete(saved.id) is False
    assert len(await repo.list_all()) == 1
