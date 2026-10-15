"""Tests for SetQuantityUseCase and qty parsing."""

import pytest

from src.domain.entities import Item
from src.domain.errors import DomainError
from src.use_cases.set_quantity import SetQuantityRequest, SetQuantityUseCase, parse_qty
from tests.unit.fakes import InMemoryItemRepository


@pytest.mark.parametrize(
    ("text", "expected"),
    [("1", 1), ("2", 2), ("3 шт", 3), (" 10ШТ ", 10)],
)
def test_parse_qty_valid(text: str, expected: int) -> None:
    assert parse_qty(text) == expected


@pytest.mark.parametrize("text", ["", "0", "-2", "abc", "1.5", "шт"])
def test_parse_qty_invalid(text: str) -> None:
    with pytest.raises(DomainError):
        parse_qty(text)


async def test_set_quantity_ok() -> None:
    repo = InMemoryItemRepository()
    item = await repo.add(Item(url="https://ozon.ru/product/x-1", created_by=1))
    assert item.id is not None
    response = await SetQuantityUseCase(repo).execute(
        SetQuantityRequest(item_id=item.id, qty_text="3")
    )
    assert response.item.qty == 3


async def test_set_quantity_rejects_zero() -> None:
    repo = InMemoryItemRepository()
    item = await repo.add(Item(url="https://ozon.ru/product/x-1", created_by=1))
    assert item.id is not None
    with pytest.raises(DomainError):
        await SetQuantityUseCase(repo).execute(SetQuantityRequest(item_id=item.id, qty_text="0"))


async def test_qty_default_is_one() -> None:
    assert Item(url="https://ozon.ru/product/x-1", created_by=1).qty == 1
    with pytest.raises(DomainError):
        Item(url="https://ozon.ru/product/x-1", created_by=1, qty=0)
