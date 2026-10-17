"""Async engine / session factory / schema init (SQLite + Postgres)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.adapters.persistence.models import Base


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(normalize_database_url(database_url), future=True)


def normalize_database_url(database_url: str) -> URL:
    """Make a user-supplied URL usable by the async engine.

    - Bare ``postgresql://`` (what Neon/Heroku hand out) defaults to the sync
      psycopg2 driver; point it at ``asyncpg`` instead.
    - Neon appends ``?sslmode=require&channel_binding=require``; asyncpg has no
      such knobs — it takes ``ssl`` (the sslmode string) and rejects unknown
      params. Translate, dropping the rest.
    """
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        return url
    if url.drivername == "postgresql":  # no explicit driver -> asyncpg
        url = url.set(drivername="postgresql+asyncpg")
    elif url.get_driver_name() != "asyncpg":
        return url  # an explicit non-asyncpg driver: leave the choice alone
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = sslmode
    return url.set(query=query)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    """Prepare the schema for local SQLite runs.

    SQLite (local/tests): create missing tables and enable WAL.
    Postgres (Neon): schema is owned by Alembic — never ``create_all`` here, or
    tables would exist without an ``alembic_version`` stamp and the first
    ``alembic upgrade head`` would fail on ``CREATE TABLE``.
    """
    if engine.url.get_backend_name() != "sqlite":
        return
    db_file = _sqlite_file(str(engine.url))
    if db_file:
        db_file.parent.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA journal_mode=WAL"))


def _sqlite_file(database_url: str) -> Path | None:
    database = make_url(database_url).database
    if not database or database == ":memory:":
        return None
    return Path(database)
