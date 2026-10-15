"""Tests for CalcStatsUseCase (counts + prepaid refunds)."""

from src.domain.entities import Item, ItemStatus, PaymentType
from src.use_cases.calc_stats import CalcStatsUseCase
from tests.unit.fakes import InMemoryItemRepository


async def _seed() -> InMemoryItemRepository:
    repo = InMemoryItemRepository()
    specs = [
        (ItemStatus.NEW, None, None),
        (ItemStatus.ORDERED, PaymentType.PREPAID, 100000),
        (ItemStatus.RECEIVED, PaymentType.PREPAID, 50000),
        (ItemStatus.CANCELLED, PaymentType.PREPAID, 30000),
        (ItemStatus.CANCELLED, PaymentType.POSTPAID, 20000),
    ]
    for index, (status, payment, price) in enumerate(specs):
        item = Item(url=f"https://ozon.ru/product/x-{index}", created_by=1)
        if price is not None:
            item.set_price(price)
        if status is not ItemStatus.NEW:
            item.transition(status)
        if payment is not None:
            item.set_payment(payment)
        await repo.add(item)
    return repo


async def test_counts_per_status() -> None:
    stats = await CalcStatsUseCase(await _seed()).execute()
    assert stats.total == 5
    assert stats.new == 1
    assert stats.ordered == 1
    assert stats.received == 1
    assert stats.cancelled == 2


async def test_returns_only_prepaid_cancelled() -> None:
    stats = await CalcStatsUseCase(await _seed()).execute()
    assert stats.returns_count == 1
    assert stats.returns_kop == 30000


async def test_empty_repo() -> None:
    stats = await CalcStatsUseCase(InMemoryItemRepository()).execute()
    assert stats.total == 0
    assert stats.returns_count == 0
