"""SetPayment use case: son marks how an item is paid (prepaid/postpaid)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import Item, ItemStatus, PaymentType
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository


@dataclass(frozen=True)
class SetPaymentRequest:
    item_id: int
    payment: PaymentType


@dataclass(frozen=True)
class SetPaymentResponse:
    item: Item


class SetPaymentUseCase:
    def __init__(self, repo: IItemRepository) -> None:
        self._repo = repo

    async def execute(self, request: SetPaymentRequest) -> SetPaymentResponse:
        item = await self._repo.get_by_id(request.item_id)
        if item is None:
            raise DomainError(f"item {request.item_id} not found")
        if item.status is ItemStatus.CANCELLED:
            raise DomainError(f"item {request.item_id} is cancelled")
        item.set_payment(request.payment)
        return SetPaymentResponse(item=await self._repo.update(item))