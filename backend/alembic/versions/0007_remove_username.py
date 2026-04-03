"""Remove username column - use email as identifier

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")


def downgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(80), nullable=True))
    # Populate username from email (part before @)
    op.execute("UPDATE users SET username = split_part(email, '@', 1)")
    op.alter_column("users", "username", nullable=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
