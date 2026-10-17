"""Tests for the manual (past-orders) debt use cases and signed parsing."""

from __future__ import annotations

import pytest

from src.domain.errors import DomainError
from src.domain.value_objects import parse_signed_price_to_kop
from src.use_cases.adjust_manual_debt import AdjustManualDebtRequest, AdjustManualDebtUseCase
from src.use_cases.set_manual_debt import SetManualDebtRequest, SetManualDebtUseCase
from tests.unit.fakes import InMemoryManualDebtRepository


async def test_adjust_adds_and_subtracts() -> None:
    repo = InMemoryManualDebtRepository()
    await AdjustManualDebtUseCase(repo).execute(AdjustManualDebtRequest(delta_kop=50000))
    response = await AdjustManualDebtUseCase(repo).execute(
        AdjustManualDebtRequest(delta_kop=-20000)
    )
    assert response.manual_debt.amount_kop == 30000


async def test_adjust_can_go_negative() -> None:
    repo = InMemoryManualDebtRepository(amount_kop=30000)
    response = await AdjustManualDebtUseCase(repo).execute(
        AdjustManualDebtRequest(delta_kop=-50000)
    )
    assert response.manual_debt.amount_kop == -20000


async def test_adjust_zero_is_rejected() -> None:
    repo = InMemoryManualDebtRepository()
    with pytest.raises(DomainError):
        await AdjustManualDebtUseCase(repo).execute(AdjustManualDebtRequest(delta_kop=0))
    assert (await repo.get()).amount_kop == 0


async def test_set_overwrites_with_signed_amount() -> None:
    repo = InMemoryManualDebtRepository(amount_kop=50000)
    response = await SetManualDebtUseCase(repo).execute(SetManualDebtRequest(amount_kop=-1500))
    assert response.manual_debt.amount_kop == -1500
    assert (await repo.get()).amount_kop == -1500


async def test_set_to_zero_resets() -> None:
    repo = InMemoryManualDebtRepository(amount_kop=70000)
    await SetManualDebtUseCase(repo).execute(SetManualDebtRequest(amount_kop=0))
    assert (await repo.get()).amount_kop == 0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 299,50", 129950),
        ("500", 50000),
        ("-500", -50000),
        ("− 500", -50000),
        ("0", 0),
    ],
)
def test_parse_signed_price(text: str, expected: int) -> None:
    assert parse_signed_price_to_kop(text) == expected


@pytest.mark.parametrize("text", ["", "-", "abc", "--5"])
def test_parse_signed_price_rejects_garbage(text: str) -> None:
    with pytest.raises(DomainError):
        parse_signed_price_to_kop(text)
