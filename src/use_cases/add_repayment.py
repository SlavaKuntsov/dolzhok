"""AddRepayment use case: executor records cash handed over by customer."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import NOTE_MAX_LEN, Repayment
from src.domain.interfaces import IRepaymentRepository


def normalize_note(raw: str | None) -> str | None:
    """Trim blank notes to None and cap length at the domain limit."""
    if raw is None:
        return None
    note = raw.strip()
    if not note:
        return None
    return note[:NOTE_MAX_LEN]


@dataclass(frozen=True)
class AddRepaymentRequest:
    amount_kop: int
    created_by: int
    note: str | None = None


@dataclass(frozen=True)
class AddRepaymentResponse:
    repayment: Repayment


class AddRepaymentUseCase:
    """Validate amount > 0 (via Repayment) and append to the ledger."""

    def __init__(self, repo: IRepaymentRepository) -> None:
        self._repo = repo

    async def execute(self, request: AddRepaymentRequest) -> AddRepaymentResponse:
        repayment = Repayment(
            amount_kop=request.amount_kop,
            created_by=request.created_by,
            note=normalize_note(request.note),
        )
        return AddRepaymentResponse(repayment=await self._repo.add(repayment))
