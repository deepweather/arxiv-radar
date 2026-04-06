"""Add paper_fulltext and paper_chunks tables for full-text indexing

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paper_fulltext",
        sa.Column("paper_id", sa.String(20), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source", sa.String(20), nullable=False, comment="ar5iv_html | pdf | marker"),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("sections", JSONB, nullable=True),
        sa.Column("char_count", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", comment="pending|extracted|failed"),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )

    op.create_table(
        "paper_chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.String(20), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("section_title", sa.String(200), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
    )
    op.create_index("ix_paper_chunks_paper_id", "paper_chunks", ["paper_id"])
    op.create_index("ix_paper_chunks_paper_chunk", "paper_chunks", ["paper_id", "chunk_index"], unique=True)


def downgrade() -> None:
    op.drop_table("paper_chunks")
    op.drop_table("paper_fulltext")
