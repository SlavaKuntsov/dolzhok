"""ListRepayments use case: repayment ledger, newest first."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import Repayment
from src.domain.interfaces import IRepaymentRepository


@dataclass(frozen=True)
class ListRepaymentsResponse:
    repayments: list[Repayment]
    total_kop: int
    count: int


class ListRepaymentsUseCase:
    def __init__(self, repo: IRepaymentRepository) -> None:
        self._repo = repo

    async def execute(self) -> ListRepaymentsResponse:
        repayments = await self._repo.list_all()
        return ListRepaymentsResponse(
            repayments=repayments,
            total_kop=sum(r.amount_kop for r in repayments),
            count=len(repayments),
        )
