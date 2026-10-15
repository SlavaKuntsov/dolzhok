"""DeleteRepayment use case: son removes a mistaken ledger entry."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.errors import DomainError
from src.domain.interfaces import IRepaymentRepository


@dataclass(frozen=True)
class DeleteRepaymentRequest:
    repayment_id: int


class DeleteRepaymentUseCase:
    def __init__(self, repo: IRepaymentRepository) -> None:
        self._repo = repo

    async def execute(self, request: DeleteRepaymentRequest) -> None:
        if not await self._repo.delete(request.repayment_id):
            raise DomainError(f"repayment {request.repayment_id} not found")
