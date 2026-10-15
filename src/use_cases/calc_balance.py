"""CalcBalance use case: outstanding debt after repayments (advance if overpaid)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.interfaces import IItemRepository, IRepaymentRepository
from src.use_cases.calc_debt import CalcDebtUseCase


@dataclass(frozen=True)
class CalcBalanceResponse:
    debt_kop: int
    debt_count: int
    repaid_kop: int
    repaid_count: int
    balance_kop: int  # debt - repaid; negative means customer overpaid
    advance_kop: int  # max(0, -balance), shown as "аванс"


class CalcBalanceUseCase:
    """Reuses CalcDebt for the debt side; repayments are the only stored money."""

    def __init__(self, item_repo: IItemRepository, repayment_repo: IRepaymentRepository) -> None:
        self._items = item_repo
        self._repayments = repayment_repo

    async def execute(self) -> CalcBalanceResponse:
        debt = await CalcDebtUseCase(self._items).execute()
        repayments = await self._repayments.list_all()
        repaid_kop = sum(r.amount_kop for r in repayments)
        balance_kop = debt.debt_kop - repaid_kop
        return CalcBalanceResponse(
            debt_kop=debt.debt_kop,
            debt_count=debt.debt_count,
            repaid_kop=repaid_kop,
            repaid_count=len(repayments),
            balance_kop=balance_kop,
            advance_kop=max(0, -balance_kop),
        )
