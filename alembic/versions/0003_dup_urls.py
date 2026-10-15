"""0003: allow duplicate URLs (drop unique constraint on items.url).

SQLite cannot drop constraints in place, so the table is rebuilt
preserving all rows. Downgrade back to unique fails if duplicates exist.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_dup_urls"
down_revision = "0002_add_qty"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items_new",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("sku", sa.String(64), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("price_kop", sa.BigInteger(), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payment", sa.String(16), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO items_new "
        "(id, url, sku, title, price_kop, qty, status, payment, created_by, created_at) "
        "SELECT id, url, sku, title, price_kop, qty, status, payment, created_by, created_at "
        "FROM items"
    )
    op.drop_table("items")
    op.rename_table("items_new", "items")
    op.create_index("ix_items_status", "items", ["status"])


def downgrade() -> None:
    op.execute("DELETE FROM items WHERE id NOT IN (SELECT MIN(id) FROM items GROUP BY url)")
    op.create_unique_constraint("uq_items_url", "items", ["url"])
