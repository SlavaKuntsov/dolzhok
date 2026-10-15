"""Tests for CalcDebtUseCase (derived debt, no stored totals)."""

import itertools

from src.domain.entities import Item, ItemStatus, PaymentType
from src.use_cases.calc_debt import CalcDebtUseCase
from tests.unit.fakes import InMemoryItemRepository

_counter = itertools.count()


async def _add(
    repo: InMemoryItemRepository,
    *,
    price: int | None,
    status: ItemStatus,
    payment: PaymentType | None,
    qty: int = 1,
) -> None:
    item = Item(url=f"https://ozon.ru/product/x-{next(_counter)}", created_by=1, qty=qty)
    if price is not None:
        item.set_price(price)
    if status is not ItemStatus.NEW:
        item.transition(status)
    if payment is not None:
        item.set_payment(payment)
    await repo.add(item)


async def test_debt_prepaid_in_work_only() -> None:
    repo = InMemoryItemRepository()
    await _add(repo, price=100000, status=ItemStatus.ORDERED, payment=PaymentType.PREPAID)
    await _add(repo, price=50000, status=ItemStatus.RECEIVED, payment=PaymentType.PREPAID)
    summary = await CalcDebtUseCase(repo).execute()
    assert summary.debt_kop == 150000
    assert summary.debt_count == 2


async def test_debt_times_qty() -> None:
    repo = InMemoryItemRepository()
    await _add(repo, price=129950, status=ItemStatus.ORDERED, payment=PaymentType.PREPAID, qty=2)
    summary = await CalcDebtUseCase(repo).execute()
    assert summary.debt_kop == 259900


async def test_cancelled_prepaid_is_not_debt() -> None:
    repo = InMemoryItemRepository()
    await _add(repo, price=100000, status=ItemStatus.CANCELLED, payment=PaymentType.PREPAID)
    summary = await CalcDebtUseCase(repo).execute()
    assert summary.debt_kop == 0
    assert summary.debt_count == 0


async def test_postpaid_ordered_is_pending_not_debt() -> None:
    repo = InMemoryItemRepository()
    await _add(repo, price=70000, status=ItemStatus.ORDERED, payment=PaymentType.POSTPAID)
    summary = await CalcDebtUseCase(repo).execute()
    assert summary.debt_kop == 0
    assert summary.postpaid_kop == 70000
    assert summary.postpaid_count == 1


async def test_postpaid_received_is_settled() -> None:
    repo = InMemoryItemRepository()
    await _add(repo, price=70000, status=ItemStatus.RECEIVED, payment=PaymentType.POSTPAID)
    summary = await CalcDebtUseCase(repo).execute()
    assert summary.debt_kop == 0
    assert summary.postpaid_kop == 0


async def test_items_without_price_are_skipped() -> None:
    repo = InMemoryItemRepository()
    await _add(repo, price=None, status=ItemStatus.ORDERED, payment=PaymentType.PREPAID)
    summary = await CalcDebtUseCase(repo).execute()
    assert summary.debt_kop == 0
    assert summary.debt_count == 0
