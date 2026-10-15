"""Ports: abstract interfaces the domain/use-cases depend on."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities import Item


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
    async def update(self, item: Item) -> Item:
        """Persist changes of an existing item."""


class IUrlResolver(ABC):
    """Resolves short links (ozo.ru) to canonical URLs. Network lives here."""

    @abstractmethod
    async def resolve(self, url: str) -> str:
        """Follow redirects and return the final URL (or input on failure)."""
