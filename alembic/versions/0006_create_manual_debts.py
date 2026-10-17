"""0006: create manual_debts table (single running past-orders figure)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_create_manual_debts"
down_revision = "0005_create_repayments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manual_debts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("amount_kop", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_manual_debts_single_row"),
    )


def downgrade() -> None:
    op.drop_table("manual_debts")
