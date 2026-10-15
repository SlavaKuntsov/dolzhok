"""AddItem use case: ingest an Ozon URL with dedup."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain import ozon
from src.domain.entities import Item
from src.domain.interfaces import IItemRepository, IUrlResolver


@dataclass(frozen=True)
class AddItemRequest:
    raw_url: str
    from_user_id: int
    title: str | None = None


@dataclass(frozen=True)
class AddItemResponse:
    item: Item


class AddItemUseCase:
    """Normalize URL, resolve short links, always create a new Item(NEW)."""

    def __init__(self, repo: IItemRepository, resolver: IUrlResolver) -> None:
        self._repo = repo
        self._resolver = resolver

    async def execute(self, request: AddItemRequest) -> AddItemResponse:
        url = ozon.normalize_url(request.raw_url)
        if ozon.is_short_url(url):
            url = ozon.normalize_url(await self._resolver.resolve(url))
        item = Item(
            url=url, sku=ozon.extract_sku(url), title=request.title, created_by=request.from_user_id
        )
        return AddItemResponse(item=await self._repo.add(item))
