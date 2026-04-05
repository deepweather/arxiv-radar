"""Fetch papers from arXiv API and upsert into PostgreSQL."""

import json
import logging
from datetime import timezone

import arxiv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


def _parse_paper(result: arxiv.Result) -> dict:
    arxiv_id = result.entry_id.split("/abs/")[-1]
    if "v" in arxiv_id:
        arxiv_id = arxiv_id.split("v")[0]

    return {
        "id": arxiv_id,
        "title": result.title.strip().replace("\n", " "),
        "summary": result.summary.strip().replace("\n", " "),
        "authors": [{"name": a.name} for a in result.authors],
        "categories": list(result.categories),
        "pdf_url": result.pdf_url,
        "published_at": result.published.replace(tzinfo=timezone.utc) if result.published.tzinfo is None else result.published,
        "updated_at": result.updated.replace(tzinfo=timezone.utc) if result.updated.tzinfo is None else result.updated,
    }


async def ingest_papers(db: AsyncSession, max_results: int | None = None) -> int:
    """Fetch latest papers from arXiv and upsert them. Returns count of new/updated papers."""
    categories = [c.strip() for c in settings.arxiv_categories.split(",")]
    query_str = " OR ".join(f"cat:{c}" for c in categories)
    batch_size = max_results or settings.arxiv_ingest_batch_size

    logger.info("Querying arXiv for: %s (max %d)", query_str, batch_size)

    search = arxiv.Search(
        query=query_str,
        max_results=batch_size,
        sort_by=arxiv.SortCriterion.LastUpdatedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    client = arxiv.Client(page_size=100, delay_seconds=3.0, num_retries=5)
    total = 0

    upsert_sql = text("""
        INSERT INTO papers (id, title, summary, authors, categories, pdf_url, published_at, updated_at)
        VALUES (:id, :title, :summary, CAST(:authors AS jsonb), :categories, :pdf_url, :published_at, :updated_at)
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            summary = EXCLUDED.summary,
            authors = EXCLUDED.authors,
            categories = EXCLUDED.categories,
            pdf_url = EXCLUDED.pdf_url,
            updated_at = EXCLUDED.updated_at
        WHERE papers.updated_at < EXCLUDED.updated_at
    """)

    batch = []
    for result in client.results(search):
        parsed = _parse_paper(result)
        batch.append({
            "id": parsed["id"],
            "title": parsed["title"],
            "summary": parsed["summary"],
            "authors": json.dumps(parsed["authors"]),
            "categories": parsed["categories"],
            "pdf_url": parsed["pdf_url"],
            "published_at": parsed["published_at"],
            "updated_at": parsed["updated_at"],
        })

        if len(batch) >= 50:
            for row in batch:
                await db.execute(upsert_sql, row)
            total += len(batch)
            logger.info("Upserted batch of %d papers (total: %d)", len(batch), total)
            batch = []

    if batch:
        for row in batch:
            await db.execute(upsert_sql, row)
        total += len(batch)

    await db.commit()
    logger.info("Ingest complete: processed %d papers", total)
    return total
