"""Smart backfilling service for historical arXiv papers.

Design principles:
- Resumable: state persisted in DB, can stop/restart anytime
- Chunked: small batches (100-200 papers) to avoid memory/timeout issues
- Offset-based: uses arXiv API pagination with ascending date order (oldest first)
- Rate-limited: respects arXiv API limits (3s delay between requests)
- Idempotent: safe to run multiple times

Strategy:
- Query papers sorted by SubmittedDate ASCENDING (oldest first)
- Use direct arXiv API with `start` parameter for reliable deep pagination
- Store offset in metadata, track papers_processed
- Stop when no more papers returned or reach current date

Usage:
    # From worker
    await run_backfill_batch(db, batch_size=100)
    
    # Or via CLI
    python -m app.cli backfill start --batch-size=100
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

# arXiv rate limit is ~1 request per 3 seconds
ARXIV_PAGE_SIZE = 200
ARXIV_DELAY_SECONDS = 3.0
ARXIV_API_URL = "https://export.arxiv.org/api/query"

# Backfill goes back this many years max
MAX_BACKFILL_YEARS = 15

# XML namespaces for arXiv Atom feed
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


async def get_backfill_status(db: AsyncSession) -> dict:
    """Get current backfill status."""
    result = await db.execute(
        text("SELECT * FROM backfill_state WHERE id = 'arxiv'")
    )
    row = result.fetchone()
    
    papers_count = await db.execute(text("SELECT COUNT(*) FROM papers"))
    total = papers_count.fetchone()[0]
    
    if not row:
        return {
            "status": "not_started",
            "cursor_offset": 0,
            "papers_processed": 0,
            "total_papers": total,
            "is_complete": False,
            "started_at": None,
            "last_run_at": None,
            "last_paper_date": None,
        }
    
    extra_data = row.extra_data or {}
    
    return {
        "status": "complete" if row.is_complete else "in_progress",
        "cursor_offset": extra_data.get("offset", 0),
        "papers_processed": row.papers_processed,
        "total_papers": total,
        "is_complete": row.is_complete,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "last_paper_date": row.cursor_date.isoformat() if row.cursor_date else None,
        "extra_data": extra_data,
    }


async def init_backfill(db: AsyncSession) -> dict:
    """Initialize backfill state if not exists. Returns current state."""
    result = await db.execute(
        text("SELECT id FROM backfill_state WHERE id = 'arxiv'")
    )
    if result.fetchone():
        return await get_backfill_status(db)
    
    now = datetime.now(timezone.utc)
    
    await db.execute(
        text("""
            INSERT INTO backfill_state (id, cursor_date, started_at, last_run_at, extra_data)
            VALUES ('arxiv', NULL, :now, :now, :meta)
        """),
        {
            "now": now,
            "meta": json.dumps({"offset": 0}),
        }
    )
    await db.commit()
    
    logger.info("Backfill initialized at offset 0")
    return await get_backfill_status(db)


async def _fetch_arxiv_page(
    client: httpx.AsyncClient,
    query: str,
    start: int,
    max_results: int,
) -> list[dict]:
    """Fetch one page of results directly from arXiv API.
    
    Returns list of parsed paper dicts, or empty list on error.
    """
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "ascending",
    }
    
    for attempt in range(5):
        try:
            resp = await client.get(ARXIV_API_URL, params=params)
            
            if resp.status_code == 503:
                # Rate limited, back off
                wait = 10 * (attempt + 1)
                logger.warning("arXiv rate limited (503), waiting %ds", wait)
                await asyncio.sleep(wait)
                continue
            
            if resp.status_code != 200:
                logger.error("arXiv API error: %d", resp.status_code)
                return []
            
            # Parse XML response
            root = ElementTree.fromstring(resp.text)
            papers = []
            
            for entry in root.findall(f"{ATOM_NS}entry"):
                paper = _parse_entry(entry)
                if paper:
                    papers.append(paper)
            
            return papers
            
        except Exception as e:
            logger.warning("arXiv fetch error (attempt %d): %s", attempt + 1, e)
            await asyncio.sleep(ARXIV_DELAY_SECONDS * (attempt + 1))
    
    return []


def _parse_entry(entry: ElementTree.Element) -> dict | None:
    """Parse an arXiv Atom entry into a paper dict."""
    try:
        entry_id = entry.find(f"{ATOM_NS}id").text
        arxiv_id = entry_id.split("/abs/")[-1]
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.split("v")[0]
        
        title = entry.find(f"{ATOM_NS}title").text or ""
        title = " ".join(title.split())  # Normalize whitespace
        
        summary = entry.find(f"{ATOM_NS}summary").text or ""
        summary = " ".join(summary.split())
        
        # Parse dates
        published_str = entry.find(f"{ATOM_NS}published").text
        updated_str = entry.find(f"{ATOM_NS}updated").text
        
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
        
        # Parse authors
        authors = []
        for author in entry.findall(f"{ATOM_NS}author"):
            name_elem = author.find(f"{ATOM_NS}name")
            if name_elem is not None and name_elem.text:
                authors.append({"name": name_elem.text})
        
        # Parse categories
        categories = []
        for cat in entry.findall(f"{ARXIV_NS}primary_category"):
            term = cat.get("term")
            if term:
                categories.append(term)
        for cat in entry.findall(f"{ATOM_NS}category"):
            term = cat.get("term")
            if term and term not in categories:
                categories.append(term)
        
        # Get PDF link
        pdf_url = None
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")
                break
        
        return {
            "id": arxiv_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "pdf_url": pdf_url,
            "published_at": published,
            "updated_at": updated,
        }
    except Exception as e:
        logger.warning("Failed to parse arXiv entry: %s", e)
        return None


async def run_backfill_batch(
    db: AsyncSession,
    batch_size: int = 100,
    dry_run: bool = False,
) -> dict:
    """Run one batch of backfill using direct arXiv API calls.
    
    Uses direct HTTP requests with proper `start` parameter for reliable
    deep pagination, avoiding the arxiv library's pagination quirks.
    
    Args:
        db: Database session
        batch_size: Papers to fetch per batch (100-500 recommended)
        dry_run: If True, don't actually insert papers
        
    Returns:
        Dict with stats: papers_fetched, new_papers, cursor_offset, is_complete
    """
    await init_backfill(db)
    
    result = await db.execute(
        text("SELECT * FROM backfill_state WHERE id = 'arxiv'")
    )
    state = result.fetchone()
    
    if state.is_complete:
        logger.info("Backfill already complete")
        return {"status": "complete", "papers_fetched": 0, "new_papers": 0, "is_complete": True}
    
    extra_data = state.extra_data or {}
    current_offset = extra_data.get("offset", 0)
    
    # Stop when we reach papers from 30 days ago (normal ingest handles recent)
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    
    # Build category query
    categories = [c.strip() for c in settings.arxiv_categories.split(",")]
    query_str = " OR ".join(f"cat:{c}" for c in categories)
    
    logger.info(
        "Backfill: offset=%d, batch_size=%d, categories=%s", 
        current_offset, batch_size, categories
    )
    
    papers_fetched = 0
    new_papers = 0
    newest_date = state.cursor_date
    reached_recent = False
    
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
        RETURNING (xmax = 0) as inserted
    """)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        papers = await _fetch_arxiv_page(client, query_str, current_offset, batch_size)
        
        if not papers:
            logger.info("No papers returned from arXiv API")
        
        for paper in papers:
            published = paper["published_at"]
            
            # Check if we've reached recent papers
            if published >= recent_cutoff:
                reached_recent = True
                logger.info("Reached recent papers (%s), stopping", published.date())
                break
            
            # Track newest date seen
            if newest_date is None or published > newest_date:
                newest_date = published
            
            if not dry_run:
                row_result = await db.execute(upsert_sql, {
                    "id": paper["id"],
                    "title": paper["title"],
                    "summary": paper["summary"],
                    "authors": json.dumps(paper["authors"]),
                    "categories": paper["categories"],
                    "pdf_url": paper["pdf_url"],
                    "published_at": published,
                    "updated_at": paper["updated_at"],
                })
                row = row_result.fetchone()
                if row and row.inserted:
                    new_papers += 1
            
            papers_fetched += 1
        
        if papers_fetched > 0 and papers_fetched % 50 == 0:
            logger.info(
                "Backfill progress: %d papers, %d new, latest: %s", 
                papers_fetched, new_papers, newest_date.date() if newest_date else "N/A"
            )
    
    # Backfill complete if: no papers returned OR reached recent papers
    is_complete = (papers_fetched == 0 and len(papers) == 0) or reached_recent
    
    if not dry_run:
        now = datetime.now(timezone.utc)
        new_offset = current_offset + papers_fetched
        total_processed = state.papers_processed + papers_fetched
        
        if is_complete:
            await _mark_complete(db, total_processed)
        else:
            new_extra_data = {**extra_data, "offset": new_offset}
            await db.execute(
                text("""
                    UPDATE backfill_state 
                    SET cursor_date = :cursor, papers_processed = :total, 
                        last_run_at = :now, extra_data = :meta
                    WHERE id = 'arxiv'
                """),
                {
                    "cursor": newest_date, 
                    "total": total_processed, 
                    "now": now,
                    "meta": json.dumps(new_extra_data),
                }
            )
        
        await db.commit()
    
    result = {
        "status": "complete" if is_complete else "in_progress",
        "papers_fetched": papers_fetched,
        "new_papers": new_papers,
        "cursor_offset": current_offset + papers_fetched,
        "last_paper_date": newest_date.isoformat() if newest_date else None,
        "is_complete": is_complete,
    }
    
    logger.info("Backfill batch done: %s", result)
    return result


async def _mark_complete(db: AsyncSession, total_processed: int) -> None:
    """Mark backfill as complete."""
    now = datetime.now(timezone.utc)
    await db.execute(
        text("""
            UPDATE backfill_state 
            SET is_complete = true, papers_processed = :total, last_run_at = :now
            WHERE id = 'arxiv'
        """),
        {"total": total_processed, "now": now}
    )
    logger.info("Backfill marked complete with %d papers processed", total_processed)


async def reset_backfill(db: AsyncSession) -> None:
    """Reset backfill state to start over."""
    await db.execute(text("DELETE FROM backfill_state WHERE id = 'arxiv'"))
    await db.commit()
    logger.info("Backfill state reset")
