"""0005: create repayments ledger table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005_create_repayments"
down_revision = "0004_drop_to_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repayments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("amount_kop", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.String(256), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("repayments")
