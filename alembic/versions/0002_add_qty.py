"""0002: add qty column to items (default 1)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_add_qty"
down_revision = "0001_create_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("qty", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("items", "qty")
