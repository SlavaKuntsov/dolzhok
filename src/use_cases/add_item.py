"""AddItem use case: ingest an Ozon URL as a new item (no dedup, no network)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain import ozon
from src.domain.entities import Item
from src.domain.interfaces import IItemRepository


@dataclass(frozen=True)
class AddItemRequest:
    raw_url: str
    from_user_id: int
    title: str | None = None


@dataclass(frozen=True)
class AddItemResponse:
    item: Item


class AddItemUseCase:
    """Normalize URL and always create a new Item(NEW). Short links are kept as-is."""

    def __init__(self, repo: IItemRepository) -> None:
        self._repo = repo

    async def execute(self, request: AddItemRequest) -> AddItemResponse:
        url = ozon.normalize_url(request.raw_url)
        item = Item(
            url=url, sku=ozon.extract_sku(url), title=request.title, created_by=request.from_user_id
        )
        return AddItemResponse(item=await self._repo.add(item))
