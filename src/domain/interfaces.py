"""Ports: abstract interfaces the domain/use-cases depend on."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities import Item, ManualDebt, Repayment


class IItemRepository(ABC):
    """Async persistence port for Item aggregates."""

    @abstractmethod
    async def add(self, item: Item) -> Item:
        """Persist a new item, return it with assigned id."""

    @abstractmethod
    async def get_by_id(self, item_id: int) -> Item | None:
        """Return item by id or None."""

    @abstractmethod
    async def find_by_url(self, url: str) -> Item | None:
        """Return item with the exact normalized URL or None."""

    @abstractmethod
    async def list_recent(self, limit: int = 10, offset: int = 0) -> list[Item]:
        """Return newest items first."""

    @abstractmethod
    async def list_all(self) -> list[Item]:
        """Return every item (newest first). Used for derived debt/stats."""

    @abstractmethod
    async def update(self, item: Item) -> Item:
        """Persist changes of an existing item."""


class IManualDebtRepository(ABC):
    """Async persistence port for the single past-orders debt figure."""

    @abstractmethod
    async def get(self) -> ManualDebt:
        """Return the stored figure, or zero when nothing was entered yet."""

    @abstractmethod
    async def save(self, manual_debt: ManualDebt) -> ManualDebt:
        """Store the figure (single row), return it as persisted."""


class IRepaymentRepository(ABC):
    """Async persistence port for the Repayment ledger."""

    @abstractmethod
    async def add(self, repayment: Repayment) -> Repayment:
        """Persist a new repayment, return it with assigned id."""

    @abstractmethod
    async def list_all(self) -> list[Repayment]:
        """Return every repayment, newest first."""

    @abstractmethod
    async def delete(self, repayment_id: int) -> bool:
        """Delete by id; return False when nothing matched."""
