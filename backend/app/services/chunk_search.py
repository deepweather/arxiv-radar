"""Semantic search over paper chunks for full-text retrieval."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embeddings import _get_model

logger = logging.getLogger(__name__)


async def search_chunks(
    db: AsyncSession,
    query: str,
    limit: int = 10,
    categories: list[str] | None = None,
    days: int | None = None,
) -> list[dict]:
    """Semantic search across paper chunks. Returns chunks with paper metadata."""
    model = _get_model()
    query_embedding = model.encode([query], normalize_embeddings=True)[0]

    params: dict = {
        "query_emb": str(query_embedding.tolist()),
        "limit": limit,
    }

    filters = []
    if categories:
        filters.append("p.categories && :cats")
        params["cats"] = categories
    if days:
        filters.append("p.published_at > NOW() - make_interval(days => :days)")
        params["days"] = days

    where = " AND ".join(filters) if filters else "1=1"

    sql = text(f"""
        SELECT
            pc.id AS chunk_id,
            pc.paper_id,
            pc.chunk_index,
            pc.section_title,
            pc.content AS chunk_content,
            pc.token_count,
            1 - (pc.embedding <=> CAST(:query_emb AS vector)) AS similarity,
            p.title AS paper_title,
            p.summary AS paper_summary,
            p.authors,
            p.categories,
            p.pdf_url,
            p.published_at,
            p.updated_at
        FROM paper_chunks pc
        JOIN papers p ON p.id = pc.paper_id
        WHERE pc.embedding IS NOT NULL AND {where}
        ORDER BY pc.embedding <=> CAST(:query_emb AS vector)
        LIMIT :limit
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()

    return [
        {
            "chunk_id": row.chunk_id,
            "paper_id": row.paper_id,
            "chunk_index": row.chunk_index,
            "section_title": row.section_title,
            "content": row.chunk_content,
            "token_count": row.token_count,
            "similarity": round(float(row.similarity), 4),
            "paper": {
                "id": row.paper_id,
                "title": row.paper_title,
                "summary": row.paper_summary,
                "authors": row.authors,
                "categories": row.categories,
                "pdf_url": row.pdf_url,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            },
        }
        for row in rows
    ]


async def get_paper_fulltext(db: AsyncSession, paper_id: str) -> dict | None:
    """Retrieve the full extracted text for a paper."""
    result = await db.execute(
        text("""
            SELECT pf.paper_id, pf.source, pf.content, pf.sections, pf.char_count,
                   pf.status, pf.extracted_at,
                   p.title, p.summary, p.authors, p.categories, p.pdf_url,
                   p.published_at, p.updated_at
            FROM paper_fulltext pf
            JOIN papers p ON p.id = pf.paper_id
            WHERE pf.paper_id = :paper_id AND pf.status = 'extracted'
        """),
        {"paper_id": paper_id},
    )
    row = result.fetchone()
    if not row:
        return None

    sections = row.sections
    if isinstance(sections, str):
        import json
        try:
            sections = json.loads(sections)
        except (json.JSONDecodeError, TypeError):
            sections = None

    return {
        "paper_id": row.paper_id,
        "source": row.source,
        "content": row.content,
        "sections": sections,
        "char_count": row.char_count,
        "extracted_at": row.extracted_at.isoformat() if row.extracted_at else None,
        "paper": {
            "id": row.paper_id,
            "title": row.title,
            "summary": row.summary,
            "authors": row.authors,
            "categories": row.categories,
            "pdf_url": row.pdf_url,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        },
    }


async def get_paper_section(db: AsyncSession, paper_id: str, section_name: str) -> dict | None:
    """Retrieve a specific section from a paper's extracted text."""
    ft = await get_paper_fulltext(db, paper_id)
    if not ft or not ft.get("sections"):
        return None

    section_lower = section_name.lower()
    for section in ft["sections"]:
        if section_lower in section.get("title", "").lower():
            return {
                "paper_id": paper_id,
                "section_title": section["title"],
                "text": section["text"],
                "paper": ft["paper"],
            }

    return None
