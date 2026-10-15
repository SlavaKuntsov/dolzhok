"""CalcStats use case: per-status counts plus prepaid refunds."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import ItemStatus
from src.domain.interfaces import IItemRepository


@dataclass(frozen=True)
class CalcStatsResponse:
    total: int
    new: int
    ordered: int
    received: int
    cancelled: int
    returns_count: int
    returns_kop: int


class CalcStatsUseCase:
    """Count items per status; cancelled prepaid items count as returns."""

    def __init__(self, repo: IItemRepository) -> None:
        self._repo = repo

    async def execute(self) -> CalcStatsResponse:
        counts = {status: 0 for status in ItemStatus}
        returns_count = returns_kop = 0
        items = await self._repo.list_all()
        for item in items:
            counts[item.status] += 1
            if item.is_returned:
                returns_count += 1
                returns_kop += item.total_kop or 0
        return CalcStatsResponse(
            total=len(items),
            new=counts[ItemStatus.NEW],
            ordered=counts[ItemStatus.ORDERED],
            received=counts[ItemStatus.RECEIVED],
            cancelled=counts[ItemStatus.CANCELLED],
            returns_count=returns_count,
            returns_kop=returns_kop,
        )
