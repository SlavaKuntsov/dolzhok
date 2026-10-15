"""Async engine / session factory / schema init for SQLite."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.adapters.persistence.models import Base


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create parent dir, tables if missing (fresh volumes), enable WAL mode."""
    db_file = _sqlite_file(str(engine.url))
    if db_file:
        db_file.parent.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.url.drivername.startswith("sqlite"):
            await conn.execute(text("PRAGMA journal_mode=WAL"))


def _sqlite_file(database_url: str) -> Path | None:
    database = make_url(database_url).database
    if not database or database == ":memory:":
        return None
    return Path(database)
