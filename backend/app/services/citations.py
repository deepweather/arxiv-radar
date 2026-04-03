"""Citation fetching via Semantic Scholar API with PostgreSQL persistence.

Two entry points:
- get_citations(db, paper_id): reads from DB only, instant, used by the API endpoint
- fetch_citations_batch(db, batch_size): background worker, fetches from S2 and persists
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

S2_API = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,authors,externalIds,year,citationCount,referenceCount"
RETRY_DAYS_BY_ERROR_COUNT = {0: 3, 1: 7, 2: 14}
MAX_RETRIES = 3
REFRESH_AFTER_DAYS = 30
FETCH_DELAY_SECONDS = 3.5


async def get_citations(db: AsyncSession, paper_id: str) -> dict:
    """Read citations from DB. Returns whatever we have (may be empty if not yet fetched)."""
    row = await db.execute(
        text("SELECT data, status FROM citation_cache WHERE paper_id = :pid"),
        {"pid": paper_id},
    )
    cached = row.fetchone()
    if cached and cached.status == "fetched":
        return cached.data

    return {"citing": [], "cited_by": [], "error": None}


async def ensure_queued(db: AsyncSession, paper_id: str) -> None:
    """Make sure a paper is in the citation queue (called during ingest)."""
    await db.execute(
        text("""
            INSERT INTO citation_cache (paper_id, status, data)
            VALUES (:pid, 'pending', '{}')
            ON CONFLICT (paper_id) DO NOTHING
        """),
        {"pid": paper_id},
    )


async def fetch_citations_batch(db: AsyncSession, batch_size: int = 50) -> int:
    """Fetch citations for a batch of papers from Semantic Scholar.
    
    Processes papers in order: pending first, then stale fetched, then retries.
    Returns number of papers processed.
    """
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=REFRESH_AFTER_DAYS)

    result = await db.execute(
        text("""
            SELECT paper_id FROM citation_cache
            WHERE 
                (status = 'pending')
                OR (status = 'fetched' AND fetched_at < :stale)
                OR (status IN ('not_found', 'error') AND error_count < :max_retries 
                    AND (retry_after IS NULL OR retry_after < :now))
            ORDER BY 
                CASE status 
                    WHEN 'pending' THEN 0 
                    WHEN 'not_found' THEN 1 
                    WHEN 'error' THEN 2 
                    ELSE 3 
                END,
                paper_id ASC
            LIMIT :limit
        """),
        {"stale": stale_cutoff, "now": now, "max_retries": MAX_RETRIES, "limit": batch_size},
    )
    paper_ids = [row.paper_id for row in result.fetchall()]

    if not paper_ids:
        return 0

    processed = 0
    async with httpx.AsyncClient(timeout=15.0) as client:
        for paper_id in paper_ids:
            try:
                citation_data = await _fetch_one(client, paper_id)

                if citation_data is None:
                    error_count_row = await db.execute(
                        text("SELECT error_count FROM citation_cache WHERE paper_id = :pid"),
                        {"pid": paper_id},
                    )
                    ec_row = error_count_row.fetchone()
                    error_count = (ec_row.error_count if ec_row else 0) + 1
                    retry_days = RETRY_DAYS_BY_ERROR_COUNT.get(error_count - 1, 30)

                    await db.execute(
                        text("""
                            UPDATE citation_cache 
                            SET status = 'not_found', error_count = :ec, 
                                retry_after = :retry
                            WHERE paper_id = :pid
                        """),
                        {"pid": paper_id, "ec": error_count,
                         "retry": now + timedelta(days=retry_days)},
                    )
                elif citation_data == "rate_limited":
                    logger.warning("S2 rate limited, stopping batch")
                    await db.commit()
                    break
                else:
                    await db.execute(
                        text("""
                            UPDATE citation_cache 
                            SET status = 'fetched', data = :data, fetched_at = :now,
                                error_count = 0, retry_after = NULL
                            WHERE paper_id = :pid
                        """),
                        {"pid": paper_id, "data": _to_json(citation_data), "now": now},
                    )

                processed += 1

                if processed % 10 == 0:
                    await db.commit()

            except Exception:
                logger.exception("Failed to fetch citations for %s", paper_id)
                await db.execute(
                    text("""
                        UPDATE citation_cache 
                        SET status = 'error', 
                            error_count = error_count + 1,
                            retry_after = :retry
                        WHERE paper_id = :pid
                    """),
                    {"pid": paper_id, "retry": now + timedelta(days=7)},
                )

            import asyncio
            await asyncio.sleep(FETCH_DELAY_SECONDS)

    await db.commit()
    logger.info("Citation fetch: processed %d papers", processed)
    return processed


async def _fetch_one(client: httpx.AsyncClient, arxiv_id: str) -> dict | str | None:
    """Fetch citations for one paper. Returns dict on success, None if not found, 'rate_limited' on 429."""
    paper_url = f"{S2_API}/paper/ARXIV:{arxiv_id}"

    refs_resp = await client.get(
        f"{paper_url}/references",
        params={"fields": S2_FIELDS, "limit": 50},
    )
    if refs_resp.status_code == 429:
        return "rate_limited"
    if refs_resp.status_code == 404:
        return None

    cites_resp = await client.get(
        f"{paper_url}/citations",
        params={"fields": S2_FIELDS, "limit": 50},
    )
    if cites_resp.status_code == 429:
        return "rate_limited"

    result = {"citing": [], "cited_by": [], "error": None}

    if refs_resp.status_code == 200:
        for item in refs_resp.json().get("data", []):
            cited = item.get("citedPaper", {})
            if cited and cited.get("title"):
                result["citing"].append(_normalize(cited))

    if cites_resp.status_code == 200:
        for item in cites_resp.json().get("data", []):
            citing = item.get("citingPaper", {})
            if citing and citing.get("title"):
                result["cited_by"].append(_normalize(citing))

    return result


def _normalize(paper: dict) -> dict:
    ext_ids = paper.get("externalIds", {}) or {}
    return {
        "title": paper.get("title", ""),
        "authors": [a.get("name", "") for a in (paper.get("authors") or [])[:5]],
        "year": paper.get("year"),
        "arxiv_id": ext_ids.get("ArXiv"),
        "citation_count": paper.get("citationCount"),
    }


def _to_json(data: dict) -> str:
    import json
    return json.dumps(data)
