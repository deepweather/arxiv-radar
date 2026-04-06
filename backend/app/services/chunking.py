"""Section-aware chunking of extracted paper full text."""

import json
import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64


def _approx_token_count(s: str) -> int:
    """Rough token estimate: split on whitespace + punctuation boundaries."""
    return len(re.findall(r"\S+", s))


def _split_text_into_chunks(
    body: str,
    section_title: str | None,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    """Split a block of text into overlapping chunks of approximately chunk_size tokens."""
    words = body.split()
    if not words:
        return []

    chunks: list[dict] = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        content = " ".join(chunk_words)

        if section_title:
            content = f"[{section_title}] {content}"

        chunks.append({
            "section_title": section_title,
            "content": content,
            "token_count": len(chunk_words),
        })

        if end >= len(words):
            break

        start = end - chunk_overlap

    return chunks


def chunk_paper(
    sections: list[dict],
    fallback_text: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """Produce indexed chunks from a paper's sections (or raw text).

    Each returned dict has: chunk_index, section_title, content, token_count.
    """
    all_chunks: list[dict] = []

    if sections:
        for section in sections:
            title = section.get("title")
            body = section.get("text", "")
            if not body.strip():
                continue
            section_chunks = _split_text_into_chunks(body, title, chunk_size, chunk_overlap)
            all_chunks.extend(section_chunks)
    elif fallback_text:
        all_chunks = _split_text_into_chunks(fallback_text, None, chunk_size, chunk_overlap)

    for i, chunk in enumerate(all_chunks):
        chunk["chunk_index"] = i

    return all_chunks


async def chunk_extracted_papers(
    db: AsyncSession,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    batch_size: int = 50,
) -> int:
    """Chunk papers that have been extracted but not yet chunked. Returns count of papers chunked."""

    result = await db.execute(text("""
        SELECT pf.paper_id, pf.content, pf.sections
        FROM paper_fulltext pf
        WHERE pf.status = 'extracted'
          AND NOT EXISTS (
              SELECT 1 FROM paper_chunks pc WHERE pc.paper_id = pf.paper_id
          )
        ORDER BY pf.extracted_at DESC
        LIMIT :batch_size
    """), {"batch_size": batch_size})
    rows = result.fetchall()

    if not rows:
        logger.info("No papers need chunking")
        return 0

    logger.info("Chunking %d papers", len(rows))

    insert_sql = text("""
        INSERT INTO paper_chunks (paper_id, chunk_index, section_title, content, token_count)
        VALUES (:paper_id, :chunk_index, :section_title, :content, :token_count)
        ON CONFLICT (paper_id, chunk_index) DO UPDATE SET
            section_title = EXCLUDED.section_title,
            content = EXCLUDED.content,
            token_count = EXCLUDED.token_count,
            embedding = NULL
    """)

    total_chunks = 0
    for row in rows:
        sections = row.sections if isinstance(row.sections, list) else None
        if sections is None and isinstance(row.sections, str):
            try:
                sections = json.loads(row.sections)
            except (json.JSONDecodeError, TypeError):
                sections = None

        chunks = chunk_paper(
            sections=sections or [],
            fallback_text=row.content,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk in chunks:
            await db.execute(insert_sql, {
                "paper_id": row.paper_id,
                "chunk_index": chunk["chunk_index"],
                "section_title": chunk.get("section_title"),
                "content": chunk["content"],
                "token_count": chunk["token_count"],
            })

        total_chunks += len(chunks)
        logger.debug("Paper %s: %d chunks", row.paper_id, len(chunks))

    await db.commit()
    logger.info("Chunking complete: %d papers, %d chunks total", len(rows), total_chunks)
    return len(rows)
