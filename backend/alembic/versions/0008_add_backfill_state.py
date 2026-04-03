"""Add backfill_state table for tracking backfill progress.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backfill_state",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("cursor_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_complete", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("papers_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("backfill_state")
