"""SQLAlchemy implementation of IManualDebtRepository (single row, SQLite + Postgres)."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.models import ManualDebtModel
from src.domain.entities import ManualDebt
from src.domain.interfaces import IManualDebtRepository


def _to_entity(model: ManualDebtModel) -> ManualDebt:
    return ManualDebt(id=model.id, amount_kop=model.amount_kop, updated_at=model.updated_at)


class SqlAlchemyManualDebtRepository(IManualDebtRepository):
    """One row holds the running past-orders debt figure."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sessions = session_factory

    async def get(self) -> ManualDebt:
        async with self._sessions() as session:
            result = await session.execute(
                select(ManualDebtModel).order_by(ManualDebtModel.id).limit(1)
            )
            model = result.scalar_one_or_none()
            return _to_entity(model) if model else ManualDebt()

    async def save(self, manual_debt: ManualDebt) -> ManualDebt:
        async with self._sessions() as session:
            async with session.begin():
                model: ManualDebtModel | None = None
                if manual_debt.id is not None:
                    model = await session.get(ManualDebtModel, manual_debt.id)
                if model is None:
                    result = await session.execute(
                        select(ManualDebtModel).order_by(ManualDebtModel.id).limit(1)
                    )
                    model = result.scalar_one_or_none()
                if model is None:
                    model = ManualDebtModel(
                        amount_kop=manual_debt.amount_kop, updated_at=manual_debt.updated_at
                    )
                    session.add(model)
                else:
                    model.amount_kop = manual_debt.amount_kop
                    model.updated_at = manual_debt.updated_at
            await session.refresh(model)
            return _to_entity(model)
