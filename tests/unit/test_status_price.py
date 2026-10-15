"""Tests for SetPriceUseCase and ChangeStatusUseCase."""

import pytest

from src.domain.entities import Item, ItemStatus
from src.domain.errors import DomainError
from src.use_cases.change_status import ChangeStatusRequest, ChangeStatusUseCase
from src.use_cases.set_price import SetPriceRequest, SetPriceUseCase
from tests.unit.fakes import InMemoryItemRepository


async def _seed() -> tuple[InMemoryItemRepository, Item]:
    repo = InMemoryItemRepository()
    item = await repo.add(Item(url="https://ozon.ru/product/x-1", created_by=1))
    return repo, item


async def test_set_price_ok() -> None:
    repo, item = await _seed()
    assert item.id is not None
    response = await SetPriceUseCase(repo).execute(
        SetPriceRequest(item_id=item.id, price_text="1 299,50")
    )
    assert response.item.price_kop == 129950


async def test_set_price_bad_format() -> None:
    repo, item = await _seed()
    assert item.id is not None
    with pytest.raises(DomainError):
        await SetPriceUseCase(repo).execute(SetPriceRequest(item_id=item.id, price_text="abc"))


async def test_set_price_missing_item() -> None:
    with pytest.raises(DomainError):
        await SetPriceUseCase(InMemoryItemRepository()).execute(
            SetPriceRequest(item_id=999, price_text="100")
        )


async def test_change_status_valid_chain() -> None:
    repo, item = await _seed()
    assert item.id is not None
    use_case = ChangeStatusUseCase(repo)
    for target in (ItemStatus.TO_ORDER, ItemStatus.ORDERED, ItemStatus.RECEIVED):
        response = await use_case.execute(ChangeStatusRequest(item_id=item.id, target=target))
        assert response.item.status == target


async def test_change_status_free_jump() -> None:
    repo, item = await _seed()
    assert item.id is not None
    response = await ChangeStatusUseCase(repo).execute(
        ChangeStatusRequest(item_id=item.id, target=ItemStatus.RECEIVED)
    )
    assert response.item.status == ItemStatus.RECEIVED


async def test_change_status_same_status_raises() -> None:
    repo, item = await _seed()
    assert item.id is not None
    with pytest.raises(DomainError):
        await ChangeStatusUseCase(repo).execute(
            ChangeStatusRequest(item_id=item.id, target=ItemStatus.NEW)
        )
