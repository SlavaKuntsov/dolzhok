"""CalcBalance use case: outstanding debt after repayments (advance if overpaid)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.interfaces import IItemRepository, IManualDebtRepository, IRepaymentRepository
from src.use_cases.calc_debt import CalcDebtResponse, CalcDebtUseCase


@dataclass(frozen=True)
class CalcBalanceResponse:
    """Debt side against the single repayment pool; the rest is derived.

    Wraps the debt breakdown instead of copying its fields, so the summary can
    always explain the balance from the same numbers it prints above it.
    """

    debt: CalcDebtResponse
    repaid_kop: int
    repaid_count: int

    @property
    def total_kop(self) -> int:
        """Items debt plus the manual past-orders figure."""
        return self.debt.total_kop

    @property
    def balance_kop(self) -> int:
        """Total minus repayments; negative means the customer overpaid."""
        return self.total_kop - self.repaid_kop

    @property
    def advance_kop(self) -> int:
        """max(0, -balance), shown as "аванс"."""
        return max(0, -self.balance_kop)


class CalcBalanceUseCase:
    """Reuses CalcDebt for the debt side; repayments are the only stored money."""

    def __init__(
        self,
        item_repo: IItemRepository,
        repayment_repo: IRepaymentRepository,
        manual_repo: IManualDebtRepository,
    ) -> None:
        self._items = item_repo
        self._repayments = repayment_repo
        self._manual = manual_repo

    async def execute(self) -> CalcBalanceResponse:
        debt = await CalcDebtUseCase(self._items, self._manual).execute()
        repayments = await self._repayments.list_all()
        return CalcBalanceResponse(
            debt=debt,
            repaid_kop=sum(r.amount_kop for r in repayments),
            repaid_count=len(repayments),
        )
