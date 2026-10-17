"""Item aggregate: statuses, payment types, transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from src.domain.errors import DomainError


class ItemStatus(StrEnum):
    NEW = "NEW"
    ORDERED = "ORDERED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class PaymentType(StrEnum):
    PREPAID = "PREPAID"
    POSTPAID = "POSTPAID"


# Main pipeline order (CANCELLED lives outside it). Numbered 1..3 in UI.
PIPELINE: tuple[ItemStatus, ...] = (
    ItemStatus.NEW,
    ItemStatus.ORDERED,
    ItemStatus.RECEIVED,
)


def allowed_next(status: ItemStatus) -> frozenset[ItemStatus]:
    """Any other pipeline status is reachable (transitions are free)."""
    return frozenset(s for s in ItemStatus if s != status)


@dataclass
class Item:
    """One Ozon product link tracked between customer and executor."""

    url: str
    created_by: int
    id: int | None = None
    sku: str | None = None
    title: str | None = None
    price_kop: int | None = None
    qty: int = 1
    status: ItemStatus = ItemStatus.NEW
    payment: PaymentType = PaymentType.PREPAID
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.url:
            raise DomainError("item url must not be empty")
        if self.price_kop is not None and self.price_kop < 0:
            raise DomainError("item price must be non-negative")
        if self.qty < 1:
            raise DomainError("item qty must be at least 1")

    def set_price(self, price_kop: int) -> None:
        if price_kop < 0:
            raise DomainError("item price must be non-negative")
        self.price_kop = price_kop

    def set_qty(self, qty: int) -> None:
        if qty < 1:
            raise DomainError("item qty must be at least 1")
        self.qty = qty

    def transition(self, target: ItemStatus) -> None:
        if target == self.status:
            raise DomainError(f"item is already {self.status.value}")
        self.status = target

    def set_payment(self, payment: PaymentType) -> None:
        self.payment = payment

    @property
    def total_kop(self) -> int | None:
        """Line total (price × qty) in kopecks, or None when price is unknown."""
        if self.price_kop is None:
            return None
        return self.price_kop * self.qty

    @property
    def is_closed(self) -> bool:
        return self.status in (ItemStatus.RECEIVED, ItemStatus.CANCELLED)

    @property
    def is_returned(self) -> bool:
        """Prepaid item that got cancelled — money came back, never counts as debt."""
        return self.status is ItemStatus.CANCELLED and self.payment is PaymentType.PREPAID


NOTE_MAX_LEN = 256


@dataclass
class ManualDebt:
    """Running lump-sum debt from past orders, not tied to any item.

    Signed: a negative value means the customer overpaid on past debt, so the
    debt only shrinks when the executor explicitly subtracts an amount.
    """

    amount_kop: int = 0
    id: int | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Repayment:
    """One cash transfer from customer to executor that shrinks the running balance."""

    amount_kop: int
    created_by: int
    id: int | None = None
    note: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.amount_kop <= 0:
            raise DomainError("repayment amount must be positive")
        if self.note is not None and len(self.note) > NOTE_MAX_LEN:
            raise DomainError("repayment note is too long")
