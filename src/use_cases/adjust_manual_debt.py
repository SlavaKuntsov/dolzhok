"""AdjustManualDebt use case: add to / subtract from the past-orders debt."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import ManualDebt
from src.domain.errors import DomainError
from src.domain.interfaces import IManualDebtRepository


@dataclass(frozen=True)
class AdjustManualDebtRequest:
    delta_kop: int


@dataclass(frozen=True)
class AdjustManualDebtResponse:
    manual_debt: ManualDebt


class AdjustManualDebtUseCase:
    """Apply a signed delta to the running past-orders debt (may go negative)."""

    def __init__(self, repo: IManualDebtRepository) -> None:
        self._repo = repo

    async def execute(self, request: AdjustManualDebtRequest) -> AdjustManualDebtResponse:
        if request.delta_kop == 0:
            raise DomainError("manual debt change must not be zero")
        current = await self._repo.get()
        updated = ManualDebt(id=current.id, amount_kop=current.amount_kop + request.delta_kop)
        return AdjustManualDebtResponse(manual_debt=await self._repo.save(updated))
