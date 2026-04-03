"""Add queue fields to citation_cache for background fetching

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("citation_cache", sa.Column("status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("citation_cache", sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True))
    op.add_column("citation_cache", sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("citation_cache", "fetched_at", server_default=None, nullable=True)
    op.create_index("ix_citation_cache_status", "citation_cache", ["status"])
    # Mark existing rows as already fetched
    op.execute("UPDATE citation_cache SET status = 'fetched' WHERE fetched_at IS NOT NULL")
    # Seed pending rows for all papers not yet in the cache
    op.execute("""
        INSERT INTO citation_cache (paper_id, status, data)
        SELECT p.id, 'pending', '{}'::jsonb
        FROM papers p
        LEFT JOIN citation_cache cc ON cc.paper_id = p.id
        WHERE cc.paper_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_citation_cache_status")
    op.drop_column("citation_cache", "error_count")
    op.drop_column("citation_cache", "retry_after")
    op.drop_column("citation_cache", "status")
