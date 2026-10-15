"""CalcDebt use case: derive how much customer owes executor (no stored total)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import ItemStatus, PaymentType
from src.domain.interfaces import IItemRepository

# Items that still count as money in play (cancelled ones are out).
WORK_STATUSES: frozenset[ItemStatus] = frozenset({ItemStatus.ORDERED, ItemStatus.RECEIVED})


@dataclass(frozen=True)
class CalcDebtResponse:
    debt_kop: int
    debt_count: int
    postpaid_kop: int
    postpaid_count: int


class CalcDebtUseCase:
    """Prepaid in-work items are customer's debt; postpaid ordered items are pending."""

    def __init__(self, repo: IItemRepository) -> None:
        self._repo = repo

    async def execute(self) -> CalcDebtResponse:
        debt_kop = debt_count = postpaid_kop = postpaid_count = 0
        for item in await self._repo.list_all():
            total = item.total_kop
            if total is None:
                continue
            if item.status in WORK_STATUSES and item.payment is PaymentType.PREPAID:
                debt_kop += total
                debt_count += 1
            elif item.status is ItemStatus.ORDERED and item.payment is PaymentType.POSTPAID:
                postpaid_kop += total
                postpaid_count += 1
        return CalcDebtResponse(
            debt_kop=debt_kop,
            debt_count=debt_count,
            postpaid_kop=postpaid_kop,
            postpaid_count=postpaid_count,
        )
