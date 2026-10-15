"""ChangeStatus use case: move item along the status machine."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import Item, ItemStatus
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository


@dataclass(frozen=True)
class ChangeStatusRequest:
    item_id: int
    target: ItemStatus


@dataclass(frozen=True)
class ChangeStatusResponse:
    item: Item


class ChangeStatusUseCase:
    def __init__(self, repo: IItemRepository) -> None:
        self._repo = repo

    async def execute(self, request: ChangeStatusRequest) -> ChangeStatusResponse:
        item = await self._repo.get_by_id(request.item_id)
        if item is None:
            raise DomainError(f"item {request.item_id} not found")
        item.transition(request.target)
        return ChangeStatusResponse(item=await self._repo.update(item))
