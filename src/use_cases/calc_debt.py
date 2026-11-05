"""CalcDebt use case: derive how much customer owes executor (no stored total)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import ItemStatus, PaymentType
from src.domain.interfaces import IItemRepository, IManualDebtRepository

# Items that still count as money in play (cancelled ones are out).
WORK_STATUSES: frozenset[ItemStatus] = frozenset({ItemStatus.ORDERED, ItemStatus.RECEIVED})


@dataclass(frozen=True)
class CalcDebtResponse:
    """Item-side money split by how it is (or will be) settled.

    `debt_*` is what the executor already fronted and the customer therefore
    owes: every prepaid item in work plus every postpaid item that was received.
    `pending_*` is postpaid and still on its way — not owed until it arrives.
    """

    debt_prepaid_kop: int
    debt_prepaid_count: int
    debt_postpaid_kop: int
    debt_postpaid_count: int
    pending_kop: int
    pending_count: int
    manual_kop: int

    @property
    def debt_kop(self) -> int:
        """Everything the executor already paid for."""
        return self.debt_prepaid_kop + self.debt_postpaid_kop

    @property
    def debt_count(self) -> int:
        return self.debt_prepaid_count + self.debt_postpaid_count

    @property
    def total_kop(self) -> int:
        """Items debt plus the manually entered past-orders figure."""
        return self.debt_kop + self.manual_kop


class CalcDebtUseCase:
    """Debt is what the executor already fronted; pending postpaid is not debt.

    A postpaid item becomes debt the moment it is received (the executor paid
    Ozon to collect it), which is why RECEIVED+POSTPAID counts here. Only an
    ordered-and-postpaid item is still pending. The past-orders figure is added
    on top and may be negative (overpayment).
    """

    def __init__(self, repo: IItemRepository, manual_repo: IManualDebtRepository) -> None:
        self._repo = repo
        self._manual = manual_repo

    async def execute(self) -> CalcDebtResponse:
        debt_prepaid_kop = debt_prepaid_count = 0
        debt_postpaid_kop = debt_postpaid_count = 0
        pending_kop = pending_count = 0
        for item in await self._repo.list_all():
            total = item.total_kop
            if total is None or item.status not in WORK_STATUSES:
                continue
            if item.payment is PaymentType.PREPAID:
                debt_prepaid_kop += total
                debt_prepaid_count += 1
            elif item.status is ItemStatus.RECEIVED:
                debt_postpaid_kop += total
                debt_postpaid_count += 1
            else:
                pending_kop += total
                pending_count += 1
        manual = await self._manual.get()
        return CalcDebtResponse(
            debt_prepaid_kop=debt_prepaid_kop,
            debt_prepaid_count=debt_prepaid_count,
            debt_postpaid_kop=debt_postpaid_kop,
            debt_postpaid_count=debt_postpaid_count,
            pending_kop=pending_kop,
            pending_count=pending_count,
            manual_kop=manual.amount_kop,
        )
