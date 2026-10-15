"""SQLAlchemy implementation of IRepaymentRepository (dialect-agnostic)."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.models import RepaymentModel
from src.domain.entities import Repayment
from src.domain.interfaces import IRepaymentRepository


def _to_entity(model: RepaymentModel) -> Repayment:
    return Repayment(
        id=model.id,
        amount_kop=model.amount_kop,
        note=model.note,
        created_by=model.created_by,
        created_at=model.created_at,
    )


def _to_model(entity: Repayment) -> RepaymentModel:
    return RepaymentModel(
        id=entity.id,
        amount_kop=entity.amount_kop,
        note=entity.note,
        created_by=entity.created_by,
        created_at=entity.created_at,
    )


class SqliteRepaymentRepository(IRepaymentRepository):
    """IRepaymentRepository backed by an async SQLAlchemy session."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sessions = session_factory

    async def add(self, repayment: Repayment) -> Repayment:
        async with self._sessions() as session:
            async with session.begin():
                model = _to_model(repayment)
                session.add(model)
            await session.refresh(model)
            return _to_entity(model)

    async def list_all(self) -> list[Repayment]:
        async with self._sessions() as session:
            result = await session.execute(
                select(RepaymentModel).order_by(RepaymentModel.id.desc())
            )
            return [_to_entity(m) for m in result.scalars().all()]

    async def delete(self, repayment_id: int) -> bool:
        async with self._sessions() as session:
            async with session.begin():
                model = await session.get(RepaymentModel, repayment_id)
                if model is None:
                    return False
                await session.delete(model)
            return True
