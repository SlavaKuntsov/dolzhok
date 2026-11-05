"""CalcDebt use case: derive how much customer owes executor (no stored total)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import ItemStatus, PaymentType
from src.domain.interfaces import IItemRepository, IManualDebtRepository
from src.domain.value_objects import MoneyCount

# Items that still count as money in play (cancelled ones are out).
WORK_STATUSES: frozenset[ItemStatus] = frozenset({ItemStatus.ORDERED, ItemStatus.RECEIVED})


@dataclass(frozen=True)
class CalcDebtResponse:
    """Item-side money as the four atomic buckets the summary renders.

    Buckets are `(payment type × receipt status)` so every in-work item that
    carries money lands in exactly one of them — the classification has no gap.
    Derived views: `debt` is what the executor already fronted (anything
    prepaid, plus postpaid that arrived), `pending` is postpaid still on its way
    and therefore not owed. `unpriced_count` counts in-work items that carry no
    money — no price, or a zero line total — because those are surfaced
    separately instead of being dropped silently.
    """

    prepaid_ordered: MoneyCount = MoneyCount()
    prepaid_received: MoneyCount = MoneyCount()
    postpaid_received: MoneyCount = MoneyCount()
    postpaid_ordered: MoneyCount = MoneyCount()
    manual_kop: int = 0
    unpriced_count: int = 0

    @property
    def debt_prepaid(self) -> MoneyCount:
        return self.prepaid_ordered + self.prepaid_received

    @property
    def debt(self) -> MoneyCount:
        """Everything the executor already paid for."""
        return self.debt_prepaid + self.postpaid_received

    @property
    def pending(self) -> MoneyCount:
        return self.postpaid_ordered

    @property
    def total_kop(self) -> int:
        """Items debt plus the manually entered past-orders figure."""
        return self.debt.amount_kop + self.manual_kop


class CalcDebtUseCase:
    """Debt is what the executor already fronted; pending postpaid is not debt.

    A postpaid item becomes debt the moment it is received (the executor paid
    Ozon to collect it), which is why received postpaid counts here. Only an
    ordered-and-postpaid item is still pending. The past-orders figure is added
    on top and may be negative (overpayment).
    """

    def __init__(self, repo: IItemRepository, manual_repo: IManualDebtRepository) -> None:
        self._repo = repo
        self._manual = manual_repo

    async def execute(self) -> CalcDebtResponse:
        # The full payment×status grid: every combination has a bucket, so no
        # item can fall between branches (the bug that motivated this shape).
        buckets = {
            (payment, status): MoneyCount() for payment in PaymentType for status in WORK_STATUSES
        }
        unpriced_count = 0
        for item in await self._repo.list_all():
            if item.status not in WORK_STATUSES:
                continue
            total = item.total_kop
            if not total:
                # No price, or a zero line total: the item carries no money, so
                # it would only ever print as an invisible "0,00 BYN (1 шт)".
                unpriced_count += 1
                continue
            key = (item.payment, item.status)
            buckets[key] = buckets[key] + MoneyCount(total, 1)
        manual = await self._manual.get()
        return CalcDebtResponse(
            prepaid_ordered=buckets[(PaymentType.PREPAID, ItemStatus.ORDERED)],
            prepaid_received=buckets[(PaymentType.PREPAID, ItemStatus.RECEIVED)],
            postpaid_received=buckets[(PaymentType.POSTPAID, ItemStatus.RECEIVED)],
            postpaid_ordered=buckets[(PaymentType.POSTPAID, ItemStatus.ORDERED)],
            manual_kop=manual.amount_kop,
            unpriced_count=unpriced_count,
        )
