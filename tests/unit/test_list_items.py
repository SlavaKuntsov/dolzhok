"""Tests for ListItemsUseCase: status filter + pagination on list_all."""

import pytest

from src.domain.entities import Item, ItemStatus
from src.domain.errors import DomainError
from src.use_cases.list_items import ListItemsRequest, ListItemsUseCase
from tests.unit.fakes import InMemoryItemRepository


async def _seed(repo: InMemoryItemRepository, statuses: list[ItemStatus]) -> None:
    for index, status in enumerate(statuses):
        await repo.add(Item(url=f"https://ozon.ru/product/x-{index}", created_by=1, status=status))


async def test_empty_repo_yields_single_empty_page() -> None:
    repo = InMemoryItemRepository()
    response = await ListItemsUseCase(repo).execute()
    assert response.items == []
    assert response.total == 0
    assert response.pages == 1
    assert response.page == 0


async def test_pagination_splits_newest_first() -> None:
    repo = InMemoryItemRepository()
    await _seed(repo, [ItemStatus.NEW] * 25)
    use_case = ListItemsUseCase(repo)

    first = await use_case.execute(ListItemsRequest(page_size=10))
    assert first.total == 25
    assert first.pages == 3
    assert len(first.items) == 10
    # newest first: ids 25..16
    assert [item.id for item in first.items] == list(range(25, 15, -1))

    last = await use_case.execute(ListItemsRequest(page=2, page_size=10))
    assert [item.id for item in last.items] == [5, 4, 3, 2, 1]


async def test_out_of_range_page_clamps_to_last() -> None:
    repo = InMemoryItemRepository()
    await _seed(repo, [ItemStatus.NEW] * 12)
    response = await ListItemsUseCase(repo).execute(ListItemsRequest(page=99, page_size=10))
    assert response.page == 1
    assert len(response.items) == 2


async def test_negative_page_clamps_to_first() -> None:
    repo = InMemoryItemRepository()
    await _seed(repo, [ItemStatus.NEW] * 12)
    response = await ListItemsUseCase(repo).execute(ListItemsRequest(page=-3, page_size=10))
    assert response.page == 0


async def test_status_filter_counts_only_matching() -> None:
    repo = InMemoryItemRepository()
    await _seed(
        repo,
        [ItemStatus.NEW, ItemStatus.ORDERED, ItemStatus.NEW, ItemStatus.CANCELLED],
    )
    response = await ListItemsUseCase(repo).execute(ListItemsRequest(status=ItemStatus.NEW))
    assert response.total == 2
    assert all(item.status is ItemStatus.NEW for item in response.items)


async def test_filter_with_no_matches_is_empty_not_error() -> None:
    repo = InMemoryItemRepository()
    await _seed(repo, [ItemStatus.NEW])
    response = await ListItemsUseCase(repo).execute(ListItemsRequest(status=ItemStatus.RECEIVED))
    assert response.items == []
    assert response.total == 0
    assert response.pages == 1


async def test_invalid_page_size_raises() -> None:
    repo = InMemoryItemRepository()
    with pytest.raises(DomainError):
        await ListItemsUseCase(repo).execute(ListItemsRequest(page_size=0))
