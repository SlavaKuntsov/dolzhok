"""SetManualDebt use case: overwrite the past-orders debt (fix a typo, reset)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import ManualDebt
from src.domain.interfaces import IManualDebtRepository


@dataclass(frozen=True)
class SetManualDebtRequest:
    amount_kop: int


@dataclass(frozen=True)
class SetManualDebtResponse:
    manual_debt: ManualDebt


class SetManualDebtUseCase:
    """Replace the running past-orders debt with an exact signed amount."""

    def __init__(self, repo: IManualDebtRepository) -> None:
        self._repo = repo

    async def execute(self, request: SetManualDebtRequest) -> SetManualDebtResponse:
        current = await self._repo.get()
        updated = ManualDebt(id=current.id, amount_kop=request.amount_kop)
        return SetManualDebtResponse(manual_debt=await self._repo.save(updated))
