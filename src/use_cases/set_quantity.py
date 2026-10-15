"""SetQuantity use case: executor sets item quantity (positive integer)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import Item
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository


@dataclass(frozen=True)
class SetQuantityRequest:
    item_id: int
    qty_text: str


@dataclass(frozen=True)
class SetQuantityResponse:
    item: Item


def parse_qty(text: str) -> int:
    """Parse quantity like ``2`` or ``3 шт`` into a positive int."""
    cleaned = text.strip().lower().removesuffix("шт").strip()
    if not cleaned.isdigit():
        raise DomainError(f"invalid quantity: {text!r}")
    qty = int(cleaned)
    if qty < 1:
        raise DomainError(f"invalid quantity: {text!r}")
    return qty


class SetQuantityUseCase:
    def __init__(self, repo: IItemRepository) -> None:
        self._repo = repo

    async def execute(self, request: SetQuantityRequest) -> SetQuantityResponse:
        item = await self._repo.get_by_id(request.item_id)
        if item is None:
            raise DomainError(f"item {request.item_id} not found")
        if item.is_closed:
            raise DomainError(f"item {request.item_id} is closed")
        item.set_qty(parse_qty(request.qty_text))
        return SetQuantityResponse(item=await self._repo.update(item))
