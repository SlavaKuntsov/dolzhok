"""Tests for AddItemUseCase."""

import pytest

from src.domain.entities import ItemStatus
from src.use_cases.add_item import AddItemRequest, AddItemUseCase
from tests.unit.fakes import FakeUrlResolver, InMemoryItemRepository

URL = "https://www.ozon.ru/product/phone-123456789/"


async def test_add_item_creates_new() -> None:
    use_case = AddItemUseCase(InMemoryItemRepository(), FakeUrlResolver())
    response = await use_case.execute(AddItemRequest(raw_url=URL, from_user_id=1))
    assert response.created is True
    assert response.item.id == 1
    assert response.item.url == "https://ozon.ru/product/phone-123456789"
    assert response.item.sku == "123456789"
    assert response.item.status == ItemStatus.NEW


async def test_add_item_dedup_returns_existing() -> None:
    repo = InMemoryItemRepository()
    use_case = AddItemUseCase(repo, FakeUrlResolver())
    first = await use_case.execute(AddItemRequest(raw_url=URL, from_user_id=1))
    second = await use_case.execute(
        AddItemRequest(raw_url="https://ozon.ru/product/phone-123456789", from_user_id=1)
    )
    assert second.created is False
    assert second.item.id == first.item.id


async def test_add_item_resolves_short_link() -> None:
    resolver = FakeUrlResolver({"https://ozo.ru/abc": "https://www.ozon.ru/product/x-999/"})
    use_case = AddItemUseCase(InMemoryItemRepository(), resolver)
    response = await use_case.execute(AddItemRequest(raw_url="https://ozo.ru/abc", from_user_id=1))
    assert response.created is True
    assert response.item.url == "https://ozon.ru/product/x-999"


async def test_add_item_rejects_non_ozon() -> None:
    from src.domain.errors import DomainError

    use_case = AddItemUseCase(InMemoryItemRepository(), FakeUrlResolver())
    with pytest.raises(DomainError):
        await use_case.execute(AddItemRequest(raw_url="https://example.com/x", from_user_id=1))
