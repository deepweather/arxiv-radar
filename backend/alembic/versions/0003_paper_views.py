"""Add paper_views table for anonymous view tracking

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paper_views",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.String(20), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_paper_views_paper_id", "paper_views", ["paper_id"])
    op.create_index("ix_paper_views_paper_viewed", "paper_views", ["paper_id", "viewed_at"])


def downgrade() -> None:
    op.drop_table("paper_views")
