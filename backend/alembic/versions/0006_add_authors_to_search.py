"""Add authors to full-text search

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update trigger function to include authors (JSONB array of {name: ...} -> text)
    op.execute("""
        CREATE OR REPLACE FUNCTION papers_tsv_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.tsv := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                       setweight(to_tsvector('english', COALESCE(
                           (SELECT string_agg(elem->>'name', ' ') FROM jsonb_array_elements(NEW.authors) AS elem),
                           ''
                       )), 'A') ||
                       setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    # Update trigger to also fire on authors change
    op.execute("DROP TRIGGER IF EXISTS papers_tsv_update ON papers")
    op.execute("""
        CREATE TRIGGER papers_tsv_update
        BEFORE INSERT OR UPDATE OF title, summary, authors ON papers
        FOR EACH ROW EXECUTE FUNCTION papers_tsv_trigger();
    """)

    # Rebuild tsv for all existing papers to include authors
    op.execute("""
        UPDATE papers SET tsv = 
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(
                (SELECT string_agg(elem->>'name', ' ') FROM jsonb_array_elements(authors) AS elem),
                ''
            )), 'A') ||
            setweight(to_tsvector('english', COALESCE(summary, '')), 'B');
    """)


def downgrade() -> None:
    # Revert trigger function to exclude authors
    op.execute("""
        CREATE OR REPLACE FUNCTION papers_tsv_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.tsv := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                       setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    # Revert trigger to only fire on title/summary changes
    op.execute("DROP TRIGGER IF EXISTS papers_tsv_update ON papers")
    op.execute("""
        CREATE TRIGGER papers_tsv_update
        BEFORE INSERT OR UPDATE OF title, summary ON papers
        FOR EACH ROW EXECUTE FUNCTION papers_tsv_trigger();
    """)

    # Rebuild tsv without authors
    op.execute("""
        UPDATE papers SET tsv = 
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(summary, '')), 'B');
    """)
