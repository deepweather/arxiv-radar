"""Add citation_cache table for persistent citation storage

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "citation_cache",
        sa.Column("paper_id", sa.String(20), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", JSONB(), nullable=False, server_default="{}"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("citation_cache")
