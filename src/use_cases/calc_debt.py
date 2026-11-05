"""CalcDebt use case: derive how much customer owes executor (no stored total)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import ItemStatus, PaymentType
from src.domain.interfaces import IItemRepository, IManualDebtRepository

# Items that still count as money in play (cancelled ones are out).
WORK_STATUSES: frozenset[ItemStatus] = frozenset({ItemStatus.ORDERED, ItemStatus.RECEIVED})


@dataclass(frozen=True)
class MoneyCount:
    """An amount in kopecks together with the number of items behind it."""

    amount_kop: int = 0
    count: int = 0

    def __add__(self, other: MoneyCount) -> MoneyCount:
        return MoneyCount(self.amount_kop + other.amount_kop, self.count + other.count)

    @property
    def is_empty(self) -> bool:
        return self.amount_kop == 0


@dataclass(frozen=True)
class CalcDebtResponse:
    """Item-side money as the four atomic buckets the summary renders.

    Buckets are `(payment type × receipt status)` so every in-work item lands in
    exactly one of them — the classification has no gap. Derived views:
    `debt` is what the executor already fronted (anything prepaid, plus postpaid
    that arrived), `pending` is postpaid still on its way and therefore not owed.
    `unpriced_count` counts in-work items with no price: they carry no money and
    are surfaced separately instead of being dropped silently.
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
    def debt_postpaid(self) -> MoneyCount:
        return self.postpaid_received

    @property
    def debt(self) -> MoneyCount:
        """Everything the executor already paid for."""
        return self.debt_prepaid + self.debt_postpaid

    @property
    def pending(self) -> MoneyCount:
        return self.postpaid_ordered

    @property
    def debt_kop(self) -> int:
        return self.debt.amount_kop

    @property
    def debt_count(self) -> int:
        return self.debt.count

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
        buckets = {
            (PaymentType.PREPAID, ItemStatus.ORDERED): MoneyCount(),
            (PaymentType.PREPAID, ItemStatus.RECEIVED): MoneyCount(),
            (PaymentType.POSTPAID, ItemStatus.RECEIVED): MoneyCount(),
            (PaymentType.POSTPAID, ItemStatus.ORDERED): MoneyCount(),
        }
        unpriced_count = 0
        for item in await self._repo.list_all():
            if item.status not in WORK_STATUSES:
                continue
            total = item.total_kop
            if total is None:
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
