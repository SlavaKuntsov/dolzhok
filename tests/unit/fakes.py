"""In-memory test doubles for ports (no DB, no network)."""

from __future__ import annotations

from src.domain.entities import Item
from src.domain.interfaces import IItemRepository


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
