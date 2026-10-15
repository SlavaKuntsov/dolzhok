"""SQLite implementation of IItemRepository (SQLAlchemy async)."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.models import ItemModel
from src.domain.entities import Item, ItemStatus, PaymentType
from src.domain.interfaces import IItemRepository


def _to_entity(model: ItemModel) -> Item:
    return Item(
        id=model.id,
        url=model.url,
        sku=model.sku,
        title=model.title,
        price_kop=model.price_kop,
        qty=model.qty,
        status=ItemStatus(model.status),
        payment=PaymentType(model.payment) if model.payment else None,
        created_by=model.created_by,
        created_at=model.created_at,
    )


def _to_model(entity: Item) -> ItemModel:
    return ItemModel(
        id=entity.id,
        url=entity.url,
        sku=entity.sku,
        title=entity.title,
        price_kop=entity.price_kop,
        qty=entity.qty,
        status=entity.status.value,
        payment=entity.payment.value if entity.payment else None,
        created_by=entity.created_by,
        created_at=entity.created_at,
    )


class SqliteItemRepository(IItemRepository):
    """IItemRepository backed by SQLite via SQLAlchemy async session."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sessions = session_factory

    async def add(self, item: Item) -> Item:
        async with self._sessions() as session:
            async with session.begin():
                model = _to_model(item)
                session.add(model)
            await session.refresh(model)
            return _to_entity(model)

    async def get_by_id(self, item_id: int) -> Item | None:
        async with self._sessions() as session:
            model = await session.get(ItemModel, item_id)
            return _to_entity(model) if model else None

    async def find_by_url(self, url: str) -> Item | None:
        async with self._sessions() as session:
            result = await session.execute(select(ItemModel).where(ItemModel.url == url))
            model = result.scalar_one_or_none()
            return _to_entity(model) if model else None

    async def list_recent(self, limit: int = 10, offset: int = 0) -> list[Item]:
        async with self._sessions() as session:
            result = await session.execute(
                select(ItemModel).order_by(ItemModel.id.desc()).limit(limit).offset(offset)
            )
            return [_to_entity(m) for m in result.scalars().all()]

    async def update(self, item: Item) -> Item:
        assert item.id is not None, "cannot update item without id"
        async with self._sessions() as session:
            async with session.begin():
                model = await session.get(ItemModel, item.id)
                assert model is not None, f"item {item.id} not found"
                fresh = _to_model(item)
                model.url = fresh.url
                model.sku = fresh.sku
                model.title = fresh.title
                model.price_kop = fresh.price_kop
                model.qty = fresh.qty
                model.status = fresh.status
                model.payment = fresh.payment
            return _to_entity(model)
