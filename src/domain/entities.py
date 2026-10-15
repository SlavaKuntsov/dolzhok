"""Item aggregate: statuses, payment types, transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from src.domain.errors import DomainError


class ItemStatus(StrEnum):
    NEW = "NEW"
    TO_ORDER = "TO_ORDER"
    ORDERED = "ORDERED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class PaymentType(StrEnum):
    PREPAID = "PREPAID"
    POSTPAID = "POSTPAID"


_ALLOWED_TRANSITIONS: dict[ItemStatus, frozenset[ItemStatus]] = {
    ItemStatus.NEW: frozenset({ItemStatus.TO_ORDER, ItemStatus.CANCELLED}),
    ItemStatus.TO_ORDER: frozenset({ItemStatus.ORDERED, ItemStatus.CANCELLED}),
    ItemStatus.ORDERED: frozenset({ItemStatus.RECEIVED, ItemStatus.CANCELLED}),
    ItemStatus.RECEIVED: frozenset(),
    ItemStatus.CANCELLED: frozenset(),
}


def allowed_next(status: ItemStatus) -> frozenset[ItemStatus]:
    """Return statuses reachable from the given one."""
    return _ALLOWED_TRANSITIONS[status]


@dataclass
class Item:
    """One Ozon product link tracked between dad and son."""

    url: str
    created_by: int
    id: int | None = None
    sku: str | None = None
    title: str | None = None
    price_kop: int | None = None
    status: ItemStatus = ItemStatus.NEW
    payment: PaymentType | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.url:
            raise DomainError("item url must not be empty")
        if self.price_kop is not None and self.price_kop < 0:
            raise DomainError("item price must be non-negative")

    def set_price(self, price_kop: int) -> None:
        if price_kop < 0:
            raise DomainError("item price must be non-negative")
        self.price_kop = price_kop

    def transition(self, target: ItemStatus) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.status]:
            raise DomainError(f"illegal transition {self.status.value} -> {target.value}")
        self.status = target

    @property
    def is_closed(self) -> bool:
        return self.status in (ItemStatus.RECEIVED, ItemStatus.CANCELLED)
