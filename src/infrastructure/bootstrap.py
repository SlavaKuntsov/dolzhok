"""Shared wiring: build the dispatcher and repositories from settings + engine.

Used by both the long-polling entrypoint (`src/main.py`) and the webhook ASGI
app (`src/adapters/webhook/app.py`) so routing and DI stay in one place.
"""

from __future__ import annotations

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncEngine

from src.adapters.persistence.manual_debt_repo import SqlAlchemyManualDebtRepository
from src.adapters.persistence.repayment_repo import SqlAlchemyRepaymentRepository
from src.adapters.persistence.sqlalchemy_repo import SqlAlchemyItemRepository
from src.adapters.telegram.routers import build_root_router
from src.infrastructure.config import Settings
from src.infrastructure.db import create_session_factory


def build_dispatcher(settings: Settings, engine: AsyncEngine) -> Dispatcher:
    """Wire repositories and routers into a fresh dispatcher."""
    session_factory = create_session_factory(engine)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["item_repo"] = SqlAlchemyItemRepository(session_factory)
    dispatcher["repayment_repo"] = SqlAlchemyRepaymentRepository(session_factory)
    dispatcher["manual_debt_repo"] = SqlAlchemyManualDebtRepository(session_factory)
    dispatcher["app_settings"] = settings
    dispatcher.include_router(build_root_router(settings))
    return dispatcher
