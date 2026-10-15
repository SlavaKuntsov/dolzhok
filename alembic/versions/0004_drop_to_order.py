"""0004: drop TO_ORDER status (pipeline is NEW -> ORDERED -> RECEIVED).

Data-only migration: leftover TO_ORDER rows become NEW.
Downgrade is a no-op (the distinction cannot be restored).
"""

from __future__ import annotations

from alembic import op

revision = "0004_drop_to_order"
down_revision = "0003_dup_urls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE items SET status = 'NEW' WHERE status = 'TO_ORDER'")


def downgrade() -> None:
    pass
