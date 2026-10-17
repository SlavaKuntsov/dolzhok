"""Async engine / session factory / schema init (SQLite + Postgres)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


def create_engine(database_url: str) -> AsyncEngine:
    url = normalize_database_url(database_url)
    if url.get_backend_name() == "postgresql":
        # Serverless: Neon's pooler (PgBouncer) already multiplexes connections.
        # Keeping a client-side pool across frozen invocations hands out sockets
        # Neon closed while the instance was idle -> "connection is closed".
        return create_async_engine(url, future=True, poolclass=NullPool)
    return create_async_engine(url, future=True)


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
    """Prepare the database connection for a run.

    The schema is owned by Alembic on every dialect (``make migrate`` /
    ``uv run alembic upgrade head``). Never ``create_all`` here: it would create
    tables without an ``alembic_version`` stamp, and the first
    ``alembic upgrade head`` would then fail with "table already exists".

    SQLite additionally gets its parent directory and WAL mode. When migrations
    have not been run yet, fail fast with an actionable message instead of a
    cryptic "no such table" later.
    """
    if engine.url.get_backend_name() == "sqlite":
        db_file = _sqlite_file(str(engine.url))
        if db_file:
            db_file.parent.mkdir(parents=True, exist_ok=True)
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
    await _require_schema(engine)


async def _require_schema(engine: AsyncEngine) -> None:
    """Raise a clear error when the schema has not been created by Alembic."""
    async with engine.connect() as conn:
        has_schema = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("items"))
    if not has_schema:
        raise RuntimeError(
            "Database schema is missing. Run migrations first: `make migrate` "
            "(or `uv run alembic upgrade head`)."
        )


def _sqlite_file(database_url: str) -> Path | None:
    database = make_url(database_url).database
    if not database or database == ":memory:":
        return None
    return Path(database)
