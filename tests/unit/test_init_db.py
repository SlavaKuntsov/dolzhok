"""init_db never creates tables; Alembic owns the schema on every dialect."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.persistence.models import Base
from src.infrastructure.db import create_engine, init_db


async def test_init_db_creates_no_tables(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'empty.db'}")
    try:
        with pytest.raises(RuntimeError, match="make migrate"):
            await init_db(engine)
    finally:
        await engine.dispose()


async def test_init_db_passes_when_schema_is_migrated(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'migrated.db'}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await init_db(engine)  # does not raise
    finally:
        await engine.dispose()
