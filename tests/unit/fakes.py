"""In-memory test doubles for ports (no DB, no network)."""

from __future__ import annotations

from src.domain.entities import Item, ManualDebt, Repayment
from src.domain.interfaces import IItemRepository, IManualDebtRepository, IRepaymentRepository


class InMemoryItemRepository(IItemRepository):
    def __init__(self) -> None:
        self._store: dict[int, Item] = {}
        self._seq = 0

    async def add(self, item: Item) -> Item:
        self._seq += 1
        item.id = self._seq
        self._store[item.id] = item
        return item

    async def get_by_id(self, item_id: int) -> Item | None:
        return self._store.get(item_id)

    async def find_by_url(self, url: str) -> Item | None:
        return next((i for i in self._store.values() if i.url == url), None)

    async def list_recent(self, limit: int = 10, offset: int = 0) -> list[Item]:
        return (await self.list_all())[offset : offset + limit]

    async def list_all(self) -> list[Item]:
        return sorted(self._store.values(), key=lambda i: i.id or 0, reverse=True)

    async def update(self, item: Item) -> Item:
        assert item.id is not None
        self._store[item.id] = item
        return item


class InMemoryManualDebtRepository(IManualDebtRepository):
    """Holds the single past-orders debt figure in memory."""

    def __init__(self, amount_kop: int = 0) -> None:
        self._current = ManualDebt(amount_kop=amount_kop)

    async def get(self) -> ManualDebt:
        return self._current

    async def save(self, manual_debt: ManualDebt) -> ManualDebt:
        manual_debt.id = manual_debt.id or 1
        self._current = manual_debt
        return manual_debt


class InMemoryRepaymentRepository(IRepaymentRepository):
    def __init__(self) -> None:
        self._store: dict[int, Repayment] = {}
        self._seq = 0

    async def add(self, repayment: Repayment) -> Repayment:
        self._seq += 1
        repayment.id = self._seq
        self._store[repayment.id] = repayment
        return repayment

    async def list_all(self) -> list[Repayment]:
        return sorted(self._store.values(), key=lambda r: r.id or 0, reverse=True)

    async def delete(self, repayment_id: int) -> bool:
        return self._store.pop(repayment_id, None) is not None
