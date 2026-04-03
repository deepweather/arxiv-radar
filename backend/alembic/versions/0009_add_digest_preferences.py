"""Add digest preferences to users

Revision ID: 0009
Revises: 0008
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("digest_enabled", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("digest_frequency", sa.String(20), nullable=False, server_default="daily"),
    )


def downgrade() -> None:
    op.drop_column("users", "digest_frequency")
    op.drop_column("users", "digest_enabled")
