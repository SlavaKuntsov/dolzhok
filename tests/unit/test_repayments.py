"""Tests for repayment use cases: add, list, delete, balance (in-memory, no DB)."""

from __future__ import annotations

import itertools

import pytest

from src.domain.entities import NOTE_MAX_LEN, Item, ItemStatus, PaymentType
from src.domain.errors import DomainError
from src.use_cases.add_repayment import AddRepaymentRequest, AddRepaymentUseCase, normalize_note
from src.use_cases.calc_balance import CalcBalanceUseCase
from src.use_cases.delete_repayment import DeleteRepaymentRequest, DeleteRepaymentUseCase
from src.use_cases.list_repayments import ListRepaymentsUseCase
from tests.unit.fakes import (
    InMemoryItemRepository,
    InMemoryManualDebtRepository,
    InMemoryRepaymentRepository,
)

_counter = itertools.count()


async def _add_item(
    repo: InMemoryItemRepository,
    *,
    price: int | None,
    status: ItemStatus = ItemStatus.ORDERED,
    payment: PaymentType | None = PaymentType.PREPAID,
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


async def _pay(repo: InMemoryRepaymentRepository, amount_kop: int, note: str | None = None) -> None:
    await AddRepaymentUseCase(repo).execute(
        AddRepaymentRequest(amount_kop=amount_kop, created_by=9, note=note)
    )


async def test_add_repayment_records_amount_and_note() -> None:
    repo = InMemoryRepaymentRepository()
    response = await AddRepaymentUseCase(repo).execute(
        AddRepaymentRequest(amount_kop=100000, created_by=9, note="  за сентябрь  ")
    )
    assert response.repayment.id is not None
    assert response.repayment.amount_kop == 100000
    assert response.repayment.note == "за сентябрь"
    listed = await ListRepaymentsUseCase(repo).execute()
    assert listed.count == 1
    assert listed.total_kop == 100000


@pytest.mark.parametrize("amount", [0, -1, -100])
async def test_add_repayment_rejects_non_positive(amount: int) -> None:
    repo = InMemoryRepaymentRepository()
    with pytest.raises(DomainError):
        await AddRepaymentUseCase(repo).execute(
            AddRepaymentRequest(amount_kop=amount, created_by=9)
        )
    assert (await ListRepaymentsUseCase(repo).execute()).count == 0


def test_normalize_note_trims_blanks_and_caps_length() -> None:
    assert normalize_note(None) is None
    assert normalize_note("   ") is None
    assert normalize_note("  track  ") == "track"
    assert normalize_note("x" * (NOTE_MAX_LEN + 50)) == "x" * NOTE_MAX_LEN


async def test_list_repayments_newest_first() -> None:
    repo = InMemoryRepaymentRepository()
    await _pay(repo, 100000, "first")
    await _pay(repo, 25000, "second")
    listed = await ListRepaymentsUseCase(repo).execute()
    assert [r.note for r in listed.repayments] == ["second", "first"]
    assert listed.total_kop == 125000


async def test_delete_repayment_removes_entry() -> None:
    repo = InMemoryRepaymentRepository()
    await _pay(repo, 100000)
    listed = await ListRepaymentsUseCase(repo).execute()
    repayment_id = listed.repayments[0].id
    assert repayment_id is not None
    await DeleteRepaymentUseCase(repo).execute(DeleteRepaymentRequest(repayment_id=repayment_id))
    assert (await ListRepaymentsUseCase(repo).execute()).count == 0


async def test_delete_missing_repayment_raises() -> None:
    repo = InMemoryRepaymentRepository()
    with pytest.raises(DomainError):
        await DeleteRepaymentUseCase(repo).execute(DeleteRepaymentRequest(repayment_id=404))


async def test_delete_repayment_restores_balance() -> None:
    items = InMemoryItemRepository()
    repayments = InMemoryRepaymentRepository()
    await _add_item(items, price=259900)
    await _pay(repayments, 100000)
    before = await CalcBalanceUseCase(items, repayments, InMemoryManualDebtRepository()).execute()
    listed = await ListRepaymentsUseCase(repayments).execute()
    repayment_id = listed.repayments[0].id
    assert repayment_id is not None

    await DeleteRepaymentUseCase(repayments).execute(
        DeleteRepaymentRequest(repayment_id=repayment_id)
    )

    after = await CalcBalanceUseCase(items, repayments, InMemoryManualDebtRepository()).execute()
    assert before.balance_kop == 159900
    assert after.balance_kop == 259900


async def test_balance_partial_payment() -> None:
    items = InMemoryItemRepository()
    repayments = InMemoryRepaymentRepository()
    await _add_item(items, price=259900)
    await _pay(repayments, 100000)
    balance = await CalcBalanceUseCase(items, repayments, InMemoryManualDebtRepository()).execute()
    assert balance.debt_kop == 259900
    assert balance.repaid_kop == 100000
    assert balance.balance_kop == 159900
    assert balance.advance_kop == 0


async def test_balance_full_payment_is_zero() -> None:
    items = InMemoryItemRepository()
    repayments = InMemoryRepaymentRepository()
    await _add_item(items, price=259900)
    await _pay(repayments, 259900)
    balance = await CalcBalanceUseCase(items, repayments, InMemoryManualDebtRepository()).execute()
    assert balance.balance_kop == 0
    assert balance.advance_kop == 0


async def test_balance_overpayment_is_advance() -> None:
    items = InMemoryItemRepository()
    repayments = InMemoryRepaymentRepository()
    await _add_item(items, price=100000)
    await _pay(repayments, 150000)
    balance = await CalcBalanceUseCase(items, repayments, InMemoryManualDebtRepository()).execute()
    assert balance.balance_kop == -50000
    assert balance.advance_kop == 50000


async def test_balance_counts_and_qty() -> None:
    items = InMemoryItemRepository()
    repayments = InMemoryRepaymentRepository()
    await _add_item(items, price=129950, qty=2)
    await _pay(repayments, 100000)
    await _pay(repayments, 50000)
    balance = await CalcBalanceUseCase(items, repayments, InMemoryManualDebtRepository()).execute()
    assert balance.debt_kop == 259900
    assert balance.debt_count == 1
    assert balance.repaid_count == 2


async def test_balance_skips_items_without_price() -> None:
    items = InMemoryItemRepository()
    repayments = InMemoryRepaymentRepository()
    await _add_item(items, price=None)
    await _pay(repayments, 100000)
    balance = await CalcBalanceUseCase(items, repayments, InMemoryManualDebtRepository()).execute()
    assert balance.debt_kop == 0
    assert balance.balance_kop == -100000
    assert balance.advance_kop == 100000
