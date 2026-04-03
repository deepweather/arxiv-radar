"""Fetch citation data from Semantic Scholar API with Redis caching."""

import json
import logging

import httpx
import redis.asyncio as aioredis

from app.config import settings
from app.constants import CITATION_CACHE_TTL, CITATION_ERROR_CACHE_TTL

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_citations(arxiv_id: str) -> dict:
    """Get citing and cited-by papers for a given arXiv paper."""
    r = await _get_redis()
    cache_key = f"citations:{arxiv_id}"

    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    result = {"citing": [], "cited_by": [], "error": None}

    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Resolve paper by arXiv ID
            paper_url = f"{SEMANTIC_SCHOLAR_API}/paper/ARXIV:{arxiv_id}"
            fields = "title,authors,externalIds,year,citationCount,referenceCount"

            # Get references (papers this paper cites)
            refs_resp = await client.get(
                f"{paper_url}/references",
                params={"fields": fields, "limit": 50},
                headers=headers,
            )
            if refs_resp.status_code == 200:
                refs_data = refs_resp.json()
                for item in refs_data.get("data", []):
                    cited = item.get("citedPaper", {})
                    if cited and cited.get("title"):
                        result["citing"].append(_normalize_paper(cited))

            # Get citations (papers that cite this paper)
            cites_resp = await client.get(
                f"{paper_url}/citations",
                params={"fields": fields, "limit": 50},
                headers=headers,
            )
            if cites_resp.status_code == 200:
                cites_data = cites_resp.json()
                for item in cites_data.get("data", []):
                    citing = item.get("citingPaper", {})
                    if citing and citing.get("title"):
                        result["cited_by"].append(_normalize_paper(citing))

    except httpx.TimeoutException:
        logger.warning("Semantic Scholar API timeout for %s", arxiv_id)
        result["error"] = "timeout"
    except Exception:
        logger.exception("Failed to fetch citations for %s", arxiv_id)
        result["error"] = "unknown"

    # Cache even on error (to avoid hammering the API)
    ttl = CITATION_CACHE_TTL if not result["error"] else CITATION_ERROR_CACHE_TTL
    await r.set(cache_key, json.dumps(result), ex=ttl)

    return result


def _normalize_paper(paper: dict) -> dict:
    ext_ids = paper.get("externalIds", {}) or {}
    return {
        "title": paper.get("title", ""),
        "authors": [a.get("name", "") for a in (paper.get("authors") or [])[:5]],
        "year": paper.get("year"),
        "arxiv_id": ext_ids.get("ArXiv"),
        "citation_count": paper.get("citationCount"),
    }
