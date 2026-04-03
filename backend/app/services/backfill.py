"""Smart backfilling service for historical arXiv papers.

Design principles:
- Resumable: state persisted in DB, can stop/restart anytime
- Chunked: small batches to avoid memory/timeout issues
- Date-based: uses date ranges to avoid arXiv API pagination limits
- Rate-limited: respects arXiv API limits (3s delay between requests)
- Idempotent: safe to run multiple times

Strategy:
- Query papers by date ranges (e.g., one month at a time)
- Move forward through time from oldest to newest
- Store cursor_date in DB, resume from last date
- Stop when we reach 30 days ago (normal ingest handles recent)

Note: arXiv API has a limit on the `start` parameter (~10000) so we MUST
use date-based queries for large-scale backfilling.

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
ARXIV_DELAY_SECONDS = 3.0
ARXIV_API_URL = "https://export.arxiv.org/api/query"

# Date range for each batch query (days)
BATCH_DATE_RANGE_DAYS = 30

# Start date for backfill (oldest papers to fetch)
BACKFILL_START_DATE = datetime(2010, 1, 1, tzinfo=timezone.utc)

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


async def _fetch_arxiv_by_date(
    client: httpx.AsyncClient,
    categories: list[str],
    from_date: datetime,
    to_date: datetime,
    start: int = 0,
    max_results: int = 1000,
) -> list[dict]:
    """Fetch papers from arXiv API within a date range.
    
    Uses submittedDate range query to avoid deep pagination limits.
    Returns list of parsed paper dicts, or empty list on error.
    """
    # Format dates as YYYYMMDDHHMMSS for arXiv API
    from_str = from_date.strftime("%Y%m%d%H%M%S")
    to_str = to_date.strftime("%Y%m%d%H%M%S")
    
    # Build query: (cat:cs.LG OR cat:cs.AI) AND submittedDate:[from TO to]
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    date_query = f"submittedDate:[{from_str} TO {to_str}]"
    query = f"({cat_query}) AND {date_query}"
    
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "ascending",
    }
    
    for attempt in range(5):
        try:
            resp = await client.get(ARXIV_API_URL, params=params, timeout=60.0)
            
            if resp.status_code == 503:
                wait = 10 * (attempt + 1)
                logger.warning("arXiv rate limited (503), waiting %ds", wait)
                await asyncio.sleep(wait)
                continue
            
            if resp.status_code != 200:
                logger.error("arXiv API error: %d - %s", resp.status_code, resp.text[:200])
                return []
            
            # Check for API error in response
            if "internal error" in resp.text.lower():
                logger.warning("arXiv API internal error, retrying in %ds", 10 * (attempt + 1))
                await asyncio.sleep(10 * (attempt + 1))
                continue
            
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
    batch_size: int = 1000,
    dry_run: bool = False,
) -> dict:
    """Run one batch of backfill using date-based arXiv API queries.
    
    Uses date ranges instead of offsets to avoid arXiv API pagination limits.
    Each batch fetches papers from a date range (default 30 days) and processes
    them in chunks.
    
    Args:
        db: Database session
        batch_size: Max papers to fetch per API call (1000 recommended)
        dry_run: If True, don't actually insert papers
        
    Returns:
        Dict with stats: papers_fetched, new_papers, cursor_date, is_complete
    """
    await init_backfill(db)
    
    result = await db.execute(
        text("SELECT * FROM backfill_state WHERE id = 'arxiv'")
    )
    state = result.fetchone()
    
    if state.is_complete:
        logger.info("Backfill already complete")
        return {"status": "complete", "papers_fetched": 0, "new_papers": 0, "is_complete": True}
    
    # Get current cursor date or start from beginning
    cursor_date = state.cursor_date or BACKFILL_START_DATE
    
    # Calculate date range for this batch
    from_date = cursor_date
    to_date = from_date + timedelta(days=BATCH_DATE_RANGE_DAYS)
    
    # Stop when we reach papers from 30 days ago (normal ingest handles recent)
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    
    # Check if we've completed
    if from_date >= recent_cutoff:
        logger.info("Backfill reached recent cutoff date, marking complete")
        if not dry_run:
            await _mark_complete(db, state.papers_processed)
            await db.commit()
        return {"status": "complete", "papers_fetched": 0, "new_papers": 0, "is_complete": True}
    
    # Don't go past the cutoff
    if to_date > recent_cutoff:
        to_date = recent_cutoff
    
    categories = [c.strip() for c in settings.arxiv_categories.split(",")]
    
    logger.info(
        "Backfill: date_range=%s to %s, categories=%s", 
        from_date.date(), to_date.date(), categories
    )
    
    papers_fetched = 0
    new_papers = 0
    newest_date = cursor_date
    
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
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Fetch all papers in date range (may need multiple API calls for large ranges)
        offset = 0
        total_in_range = 0
        
        while True:
            papers = await _fetch_arxiv_by_date(
                client, categories, from_date, to_date, 
                start=offset, max_results=batch_size
            )
            
            if not papers:
                break
            
            total_in_range += len(papers)
            
            for paper in papers:
                published = paper["published_at"]
                
                # Track newest date seen
                if published > newest_date:
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
            
            logger.info(
                "Backfill progress: %d papers fetched, %d new, date range %s-%s", 
                papers_fetched, new_papers, from_date.date(), to_date.date()
            )
            
            # If we got fewer papers than requested, we've exhausted this date range
            if len(papers) < batch_size:
                break
            
            # Otherwise fetch next page within same date range
            offset += len(papers)
            await asyncio.sleep(ARXIV_DELAY_SECONDS)
    
    # Move cursor to end of this date range
    next_cursor = to_date
    is_complete = next_cursor >= recent_cutoff
    
    if not dry_run:
        now = datetime.now(timezone.utc)
        total_processed = state.papers_processed + papers_fetched
        
        if is_complete:
            await _mark_complete(db, total_processed)
        else:
            await db.execute(
                text("""
                    UPDATE backfill_state 
                    SET cursor_date = :cursor, papers_processed = :total, 
                        last_run_at = :now
                    WHERE id = 'arxiv'
                """),
                {
                    "cursor": next_cursor, 
                    "total": total_processed, 
                    "now": now,
                }
            )
        
        await db.commit()
    
    result = {
        "status": "complete" if is_complete else "in_progress",
        "papers_fetched": papers_fetched,
        "new_papers": new_papers,
        "cursor_date": next_cursor.isoformat(),
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
