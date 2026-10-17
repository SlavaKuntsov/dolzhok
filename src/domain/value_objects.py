"""Value objects: Money and price parsing. Pure, no frameworks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.domain.errors import DomainError

_PRICE_RE = re.compile(r"^\d[\d\s\u00a0\u2009]*([,.]\d{1,2})?$")


@dataclass(frozen=True)
class Money:
    """Non-negative amount in kopecks (minor units)."""

    amount_kop: int

    def __post_init__(self) -> None:
        if self.amount_kop < 0:
            raise DomainError("money amount must be non-negative")

    def format_rub(self) -> str:
        rubles, kop = divmod(self.amount_kop, 100)
        grouped = f"{rubles:,}".replace(",", " ")
        return f"{grouped},{kop:02d} BYN"


def parse_signed_price_to_kop(text: str) -> int:
    """Parse ``1 299,50`` or ``-500`` into signed kopecks.

    Raises:
        DomainError: if the input is not a valid amount.
    """
    cleaned = text.strip()
    sign = 1
    if cleaned[:1] in ("-", "\u2212"):
        sign = -1
        cleaned = cleaned[1:].strip()
    return sign * parse_price_to_kop(cleaned)


def parse_price_to_kop(text: str) -> int:
    """Parse human price input like ``1 299,50`` into kopecks (129950).

    Raises:
        DomainError: if the input is not a valid non-negative price.
    """
    cleaned = text.strip().replace("\u00a0", " ").replace("\u2009", " ")
    cleaned = re.sub(r"\s*(BYN|руб\.?|rub)\s*$", "", cleaned, flags=re.IGNORECASE)
    if not _PRICE_RE.match(cleaned):
        raise DomainError(f"invalid price: {text!r}")
    normalized = cleaned.replace(" ", "").replace(",", ".")
    rubles = float(normalized)
    kop = int(round(rubles * 100))
    if kop < 0:
        raise DomainError(f"invalid price: {text!r}")
    return kop
