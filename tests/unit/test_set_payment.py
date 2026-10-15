"""Tests for SetPaymentUseCase."""

import pytest

from src.domain.entities import Item, ItemStatus, PaymentType
from src.domain.errors import DomainError
from src.use_cases.set_payment import SetPaymentRequest, SetPaymentUseCase
from tests.unit.fakes import InMemoryItemRepository


async def test_set_payment_on_new_item() -> None:
    repo = InMemoryItemRepository()
    item = await repo.add(Item(url="https://ozon.ru/product/x-1", created_by=1))
    assert item.id is not None
    response = await SetPaymentUseCase(repo).execute(
        SetPaymentRequest(item_id=item.id, payment=PaymentType.PREPAID)
    )
    assert response.item.payment is PaymentType.PREPAID


async def test_set_payment_allowed_on_received() -> None:
    repo = InMemoryItemRepository()
    item = await repo.add(Item(url="https://ozon.ru/product/x-2", created_by=1))
    assert item.id is not None
    item.transition(ItemStatus.RECEIVED)
    await repo.update(item)
    response = await SetPaymentUseCase(repo).execute(
        SetPaymentRequest(item_id=item.id, payment=PaymentType.POSTPAID)
    )
    assert response.item.payment is PaymentType.POSTPAID


async def test_set_payment_rejected_on_cancelled() -> None:
    repo = InMemoryItemRepository()
    item = await repo.add(Item(url="https://ozon.ru/product/x-3", created_by=1))
    assert item.id is not None
    item.transition(ItemStatus.CANCELLED)
    await repo.update(item)
    with pytest.raises(DomainError):
        await SetPaymentUseCase(repo).execute(
            SetPaymentRequest(item_id=item.id, payment=PaymentType.PREPAID)
        )


async def test_set_payment_missing_item() -> None:
    with pytest.raises(DomainError):
        await SetPaymentUseCase(InMemoryItemRepository()).execute(
            SetPaymentRequest(item_id=999, payment=PaymentType.PREPAID)
        )