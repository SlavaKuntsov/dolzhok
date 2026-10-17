"""CalcBalance use case: outstanding debt after repayments (advance if overpaid)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.interfaces import IItemRepository, IManualDebtRepository, IRepaymentRepository
from src.use_cases.calc_debt import CalcDebtUseCase


@dataclass(frozen=True)
class CalcBalanceResponse:
    debt_kop: int
    debt_count: int
    manual_kop: int
    total_kop: int  # items debt + manual past-orders debt
    repaid_kop: int
    repaid_count: int
    balance_kop: int  # total - repaid; negative means customer overpaid
    advance_kop: int  # max(0, -balance), shown as "аванс"


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
        repaid_kop = sum(r.amount_kop for r in repayments)
        total_kop = debt.total_kop
        balance_kop = total_kop - repaid_kop
        return CalcBalanceResponse(
            debt_kop=debt.debt_kop,
            debt_count=debt.debt_count,
            manual_kop=debt.manual_kop,
            total_kop=total_kop,
            repaid_kop=repaid_kop,
            repaid_count=len(repayments),
            balance_kop=balance_kop,
            advance_kop=max(0, -balance_kop),
        )
