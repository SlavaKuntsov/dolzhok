"""Tests for AddItemUseCase."""

import pytest

from src.domain.entities import ItemStatus
from src.use_cases.add_item import AddItemRequest, AddItemUseCase
from tests.unit.fakes import InMemoryItemRepository

URL = "https://www.ozon.ru/product/phone-123456789/"


async def test_add_item_creates_new() -> None:
    use_case = AddItemUseCase(InMemoryItemRepository())
    response = await use_case.execute(AddItemRequest(raw_url=URL, from_user_id=1))
    assert response.item.id == 1
    assert response.item.url == "https://ozon.ru/product/phone-123456789"
    assert response.item.sku == "123456789"
    assert response.item.status == ItemStatus.NEW


async def test_add_item_allows_duplicates_as_separate_items() -> None:
    repo = InMemoryItemRepository()
    use_case = AddItemUseCase(repo)
    first = await use_case.execute(AddItemRequest(raw_url=URL, from_user_id=1))
    second = await use_case.execute(
        AddItemRequest(raw_url="https://ozon.ru/product/phone-123456789", from_user_id=1)
    )
    assert first.item.id != second.item.id
    assert second.item.url == first.item.url


async def test_add_item_keeps_short_link_as_is() -> None:
    use_case = AddItemUseCase(InMemoryItemRepository())
    response = await use_case.execute(
        AddItemRequest(raw_url="https://ozon.by/t/9oLOYk1", from_user_id=1, title="Втулка Д16мм")
    )
    assert response.item.url == "https://ozon.by/t/9oLOYk1"
    assert response.item.title == "Втулка Д16мм"
    assert response.item.sku is None


async def test_add_item_rejects_non_ozon() -> None:
    from src.domain.errors import DomainError

    use_case = AddItemUseCase(InMemoryItemRepository())
    with pytest.raises(DomainError):
        await use_case.execute(AddItemRequest(raw_url="https://example.com/x", from_user_id=1))
