"""ListItems use case: filter items by status and return one page (newest first)."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.entities import Item, ItemStatus
from src.domain.errors import DomainError
from src.domain.interfaces import IItemRepository

DEFAULT_PAGE_SIZE = 10


@dataclass(frozen=True)
class ListItemsRequest:
    status: ItemStatus | None = None
    page: int = 0
    page_size: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class ListItemsResponse:
    items: list[Item]
    status: ItemStatus | None
    page: int
    pages: int
    total: int
    page_size: int = field(default=DEFAULT_PAGE_SIZE)


class ListItemsUseCase:
    """Slice `list_all` by optional status filter and page. Nothing is stored."""

    def __init__(self, repo: IItemRepository) -> None:
        self._repo = repo

    async def execute(self, request: ListItemsRequest | None = None) -> ListItemsResponse:
        request = request or ListItemsRequest()
        if request.page_size < 1:
            raise DomainError("page_size must be at least 1")
        items = await self._repo.list_all()
        if request.status is not None:
            items = [item for item in items if item.status == request.status]
        total = len(items)
        pages = max(1, -(-total // request.page_size))  # ceil division
        page = min(max(request.page, 0), pages - 1)
        start = page * request.page_size
        return ListItemsResponse(
            items=items[start : start + request.page_size],
            status=request.status,
            page=page,
            pages=pages,
            total=total,
            page_size=request.page_size,
        )
