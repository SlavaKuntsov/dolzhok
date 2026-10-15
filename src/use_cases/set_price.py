"""SetPrice use case: son sets item price from free-form input."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import Item
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository
from src.domain.value_objects import parse_price_to_kop


@dataclass(frozen=True)
class SetPriceRequest:
    item_id: int
    price_text: str


@dataclass(frozen=True)
class SetPriceResponse:
    item: Item


class SetPriceUseCase:
    def __init__(self, repo: IItemRepository) -> None:
        self._repo = repo

    async def execute(self, request: SetPriceRequest) -> SetPriceResponse:
        item = await self._repo.get_by_id(request.item_id)
        if item is None:
            raise DomainError(f"item {request.item_id} not found")
        if item.is_closed:
            raise DomainError(f"item {request.item_id} is closed")
        item.set_price(parse_price_to_kop(request.price_text))
        return SetPriceResponse(item=await self._repo.update(item))
