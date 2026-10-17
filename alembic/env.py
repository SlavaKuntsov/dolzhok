"""Alembic async environment (SQLite + SQLAlchemy 2.0)."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from src.adapters.persistence.models import Base
from src.infrastructure.db import normalize_database_url

config = context.config

# Honor DATABASE_URL from .env, not just the process env, so `make migrate`
# targets the same database the app does (pydantic-settings reads .env too).
load_dotenv()

# Prefer the runtime DATABASE_URL (Neon / shell env /.env) over the alembic.ini
# default so migrations hit the right database, not a local path.
_env_url = os.environ.get("DATABASE_URL")
if _env_url:
    normalized = normalize_database_url(_env_url).render_as_string(hide_password=False)
    # set_main_option goes through ConfigParser: escape literal '%' (e.g. in a
    # password) so interpolation doesn't choke.
    config.set_main_option("sqlalchemy.url", normalized.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _ensure_sqlite_dir() -> None:
    url = config.get_main_option("sqlalchemy.url") or ""
    if url.startswith("sqlite"):
        database = make_url(url).database
        if database and database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
