"""Add collection sharing: share_slug, collection_views, is_public index

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "collections",
        sa.Column("share_slug", sa.String(60), nullable=True),
    )
    op.create_unique_constraint("uq_collections_share_slug", "collections", ["share_slug"])
    op.create_index("ix_collections_is_public", "collections", ["is_public"])

    # Backfill existing collections with a slug
    op.execute(
        "UPDATE collections SET share_slug = left(md5(id::text || random()::text), 10) WHERE share_slug IS NULL"
    )

    op.create_table(
        "collection_views",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("collection_id", UUID(as_uuid=True), sa.ForeignKey("collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_collection_views_collection_id", "collection_views", ["collection_id"])
    op.create_index("ix_collection_views_coll_viewed", "collection_views", ["collection_id", "viewed_at"])


def downgrade() -> None:
    op.drop_table("collection_views")
    op.drop_index("ix_collections_is_public", table_name="collections")
    op.drop_constraint("uq_collections_share_slug", "collections")
    op.drop_column("collections", "share_slug")
