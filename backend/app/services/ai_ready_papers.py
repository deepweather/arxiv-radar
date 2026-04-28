"""Lazy generation of AI-readable paper markdown with a local artifact cache."""

import asyncio
import json
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import arxiv
import httpx
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.fulltext import (
    AR5IV_BASE,
    ARXIV_PDF_BASE,
    _extract_sections_from_html,
    _extract_text_from_pdf_bytes,
    _try_latex_source,
)
from app.services.search import get_paper

logger = logging.getLogger(__name__)

_ARXIV_ID_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
_VERSION_SUFFIX_RE = re.compile(r"v\d+$", re.IGNORECASE)
_redis: aioredis.Redis | None = None


class AIReadyPaperError(Exception):
    """Raised when an AI-ready paper cannot be generated."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def normalize_arxiv_id(raw_paper_id: str) -> str:
    """Normalize arXiv IDs from route params, URLs, or versioned IDs."""
    paper_id = _clean_arxiv_identifier(raw_paper_id)
    paper_id = _VERSION_SUFFIX_RE.sub("", paper_id)
    if not paper_id or not _ARXIV_ID_RE.match(paper_id):
        raise AIReadyPaperError(400, "Invalid arXiv ID")
    return paper_id


def _clean_arxiv_identifier(raw_paper_id: str) -> str:
    paper_id = raw_paper_id.strip()
    paper_id = paper_id.removeprefix("arxiv:")
    paper_id = paper_id.removeprefix("arXiv:")

    for prefix in ("https://arxiv.org/abs/", "http://arxiv.org/abs/"):
        if paper_id.startswith(prefix):
            paper_id = paper_id[len(prefix):]

    for prefix in ("https://arxiv.org/pdf/", "http://arxiv.org/pdf/"):
        if paper_id.startswith(prefix):
            paper_id = paper_id[len(prefix):]

    if paper_id.endswith(".pdf"):
        paper_id = paper_id[:-4]

    if not paper_id or not _ARXIV_ID_RE.match(paper_id):
        raise AIReadyPaperError(400, "Invalid arXiv ID")
    return paper_id


def _extract_version(identifier: str | None) -> str | None:
    if not identifier:
        return None
    match = _VERSION_SUFFIX_RE.search(identifier)
    return match.group(0).lower() if match else None


def _versioned_id(paper_id: str, version: str | None) -> str:
    return f"{paper_id}{version}" if version else paper_id


def _requested_version(raw_paper_id: str) -> str | None:
    return _extract_version(_clean_arxiv_identifier(raw_paper_id))


def _safe_cache_stem(cache_id: str) -> str:
    return cache_id.replace("/", "_")


def _cache_dir(kind: str) -> Path:
    path = Path(settings.paper_cache_dir) / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path(kind: str, cache_id: str, suffix: str) -> Path:
    return _cache_dir(kind) / f"{_safe_cache_stem(cache_id)}{suffix}"


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp_path.write_bytes(content)
    os.replace(tmp_path, path)


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def _acquire_generation_lock(paper_id: str, ttl_seconds: int = 180) -> str:
    """Return lock token, empty string if Redis is unavailable, or raise if locked."""
    token = f"{os.getpid()}:{time.time()}:{uuid4().hex}"
    try:
        redis = await _get_redis()
        acquired = await redis.set(f"lock:ai-ready:{paper_id}", token, nx=True, ex=ttl_seconds)
    except Exception:
        logger.warning("AI-ready generation lock unavailable; proceeding without lock", exc_info=True)
        return ""

    if acquired:
        return token

    raise AIReadyPaperError(409, "Paper markdown is already being generated. Try again shortly.")


async def _release_generation_lock(paper_id: str, token: str) -> None:
    if not token:
        return
    try:
        redis = await _get_redis()
        key = f"lock:ai-ready:{paper_id}"
        if await redis.get(key) == token:
            await redis.delete(key)
    except Exception:
        logger.debug("AI-ready generation lock release failed for %s", paper_id, exc_info=True)


def _parse_arxiv_result(result: arxiv.Result) -> dict:
    identifier = result.entry_id.split("/abs/")[-1]
    arxiv_id = normalize_arxiv_id(identifier)
    version = _extract_version(identifier) or _extract_version(result.pdf_url)
    parsed = {
        "id": arxiv_id,
        "title": result.title.strip().replace("\n", " "),
        "summary": result.summary.strip().replace("\n", " "),
        "authors": json.dumps([{"name": author.name} for author in result.authors]),
        "categories": list(result.categories),
        "pdf_url": result.pdf_url,
        "published_at": result.published.replace(tzinfo=timezone.utc) if result.published.tzinfo is None else result.published,
        "updated_at": result.updated.replace(tzinfo=timezone.utc) if result.updated.tzinfo is None else result.updated,
    }
    parsed["_version"] = version
    return parsed


def _fetch_arxiv_metadata_sync(paper_id: str, version: str | None = None) -> dict | None:
    client = arxiv.Client(page_size=10, delay_seconds=3.0, num_retries=3)
    search = arxiv.Search(id_list=[_versioned_id(paper_id, version)])
    result = next(client.results(search), None)
    return _parse_arxiv_result(result) if result else None


def _paper_sql_params(parsed: dict) -> dict:
    return {key: parsed[key] for key in (
        "id",
        "title",
        "summary",
        "authors",
        "categories",
        "pdf_url",
        "published_at",
        "updated_at",
    )}


def _version_from_paper(paper: dict | None) -> str | None:
    if not paper:
        return None
    return _extract_version(paper.get("pdf_url"))


async def _upsert_paper_metadata(db: AsyncSession, parsed: dict) -> dict:
    await db.execute(
        text("""
            INSERT INTO papers (id, title, summary, authors, categories, pdf_url, published_at, updated_at)
            VALUES (:id, :title, :summary, CAST(:authors AS jsonb), :categories, :pdf_url, :published_at, :updated_at)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                summary = EXCLUDED.summary,
                authors = EXCLUDED.authors,
                categories = EXCLUDED.categories,
                pdf_url = EXCLUDED.pdf_url,
                updated_at = EXCLUDED.updated_at
        """),
        _paper_sql_params(parsed),
    )
    paper = await get_paper(db, parsed["id"])
    if paper is None:
        raise AIReadyPaperError(500, "Paper metadata could not be stored")
    return paper


async def _ensure_paper_metadata(
    db: AsyncSession,
    paper_id: str,
    requested_version: str | None,
) -> tuple[dict, str | None, bool]:
    """Return paper metadata, content version, and whether that version is latest."""
    paper = await get_paper(db, paper_id)

    if requested_version:
        requested = await asyncio.to_thread(_fetch_arxiv_metadata_sync, paper_id, requested_version)
        if requested is None:
            raise AIReadyPaperError(404, "Paper version not found")
        if paper is None:
            latest = await asyncio.to_thread(_fetch_arxiv_metadata_sync, paper_id)
            paper = await _upsert_paper_metadata(db, latest or requested)
        return paper, requested_version, False

    parsed = await asyncio.to_thread(_fetch_arxiv_metadata_sync, paper_id)
    if parsed is None:
        if paper:
            return paper, _version_from_paper(paper), True
        raise AIReadyPaperError(404, "Paper not found")

    paper = await _upsert_paper_metadata(db, parsed)
    latest_version = parsed.get("_version") or _version_from_paper(paper)
    return paper, latest_version, True


def _authors_text(paper: dict) -> str:
    authors = paper.get("authors") or []
    if not isinstance(authors, list):
        return str(authors)
    return ", ".join(author.get("name", "") for author in authors if author.get("name"))


def _markdown_from_sections(
    paper: dict,
    source: str,
    version: str | None,
    sections: list[dict],
    fallback_text: str | None = None,
) -> str:
    lines = [
        f"# {paper.get('title', 'Untitled')}",
        "",
        f"- arXiv ID: {paper['id']}",
        f"- Version: {version or 'unknown'}",
        f"- Authors: {_authors_text(paper) or 'Unknown'}",
        f"- Categories: {', '.join(paper.get('categories') or [])}",
        f"- Published: {paper.get('published_at') or 'Unknown'}",
        f"- Source: {source}",
        f"- Abstract page: https://arxiv.org/abs/{paper['id']}",
    ]
    if paper.get("pdf_url"):
        lines.append(f"- PDF: {paper['pdf_url']}")

    if paper.get("summary"):
        lines.extend(["", "## Abstract", paper["summary"].strip()])

    if sections:
        for section in sections:
            title = re.sub(r"\s+", " ", str(section.get("title") or "Untitled")).strip()
            body = str(section.get("text") or "").strip()
            if not body:
                continue
            if title.lower() == "abstract" and paper.get("summary"):
                continue
            lines.extend(["", f"## {title}", body])
    elif fallback_text:
        lines.extend(["", "## Full Text", fallback_text.strip()])

    return "\n".join(lines).strip() + "\n"


def _is_ar5iv_html(html: str) -> bool:
    return len(html) >= 5000 and ("ltx_document" in html or "ltx_page" in html)


async def _fetch_ar5iv_html(client: httpx.AsyncClient, paper_id: str) -> str | None:
    try:
        response = await client.get(f"{AR5IV_BASE}{paper_id}", follow_redirects=True, timeout=30.0)
        if response.status_code != 200:
            return None
        final_host = str(response.url.host) if response.url else ""
        if "arxiv.org" in final_host and "ar5iv" not in final_host:
            return None
        if not _is_ar5iv_html(response.text):
            return None
        return response.text
    except Exception as exc:
        logger.debug("ar5iv fetch failed for %s: %s", paper_id, exc)
        return None


async def _download_pdf(client: httpx.AsyncClient, paper_id: str, pdf_url: str | None) -> bytes | None:
    url = pdf_url or f"{ARXIV_PDF_BASE}{paper_id}.pdf"
    try:
        response = await client.get(url, follow_redirects=True, timeout=60.0)
        if response.status_code != 200:
            return None
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type and not response.content.startswith(b"%PDF-"):
            return None
        return response.content
    except Exception as exc:
        logger.debug("PDF download failed for %s: %s", paper_id, exc)
        return None


async def _upsert_fulltext(
    db: AsyncSession,
    paper_id: str,
    source: str,
    markdown: str,
    sections: list[dict],
) -> None:
    await db.execute(
        text("""
            INSERT INTO paper_fulltext (paper_id, source, content, sections, char_count, status, extracted_at, error_message)
            VALUES (:paper_id, :source, :content, CAST(:sections AS jsonb), :char_count, 'extracted', :extracted_at, NULL)
            ON CONFLICT (paper_id) DO UPDATE SET
                source = EXCLUDED.source,
                content = EXCLUDED.content,
                sections = EXCLUDED.sections,
                char_count = EXCLUDED.char_count,
                status = EXCLUDED.status,
                extracted_at = EXCLUDED.extracted_at,
                error_message = NULL
        """),
        {
            "paper_id": paper_id,
            "source": source,
            "content": markdown,
            "sections": json.dumps(sections),
            "char_count": len(markdown),
            "extracted_at": datetime.now(timezone.utc),
        },
    )


async def _cached_content_source(db: AsyncSession, paper_id: str) -> str:
    result = await db.execute(
        text("SELECT source FROM paper_fulltext WHERE paper_id = :paper_id AND status = 'extracted'"),
        {"paper_id": paper_id},
    )
    return result.scalar_one_or_none() or "cache"


async def _generate_markdown(
    db: AsyncSession,
    paper: dict,
    version: str | None,
    update_fulltext: bool,
) -> dict:
    paper_id = paper["id"]
    content_id = _versioned_id(paper_id, version)
    markdown_path = _cache_path("markdown", content_id, ".md")
    html_path = _cache_path("html", content_id, ".html")
    pdf_path = _cache_path("pdf", content_id, ".pdf")

    async with httpx.AsyncClient(headers={"User-Agent": "arxiv-radar/1.0 (ai-ready paper)"}) as client:
        html = html_path.read_text(encoding="utf-8") if html_path.exists() else None
        if html is None:
            html = await _fetch_ar5iv_html(client, content_id)
            if html:
                _atomic_write_text(html_path, html)

        if html:
            full_text, sections = _extract_sections_from_html(html)
            markdown = _markdown_from_sections(paper, "ar5iv_html", version, sections, full_text)
            _atomic_write_text(markdown_path, markdown)
            if update_fulltext:
                await _upsert_fulltext(db, paper_id, "ar5iv_html", markdown, sections)
            return {"markdown": markdown, "source": "ar5iv_html", "sections": sections, "pdf_cached": pdf_path.exists()}

        latex_result = await _try_latex_source(client, content_id)
        if latex_result:
            full_text, sections = latex_result
            markdown = _markdown_from_sections(paper, "latex", version, sections, full_text)
            _atomic_write_text(markdown_path, markdown)
            if update_fulltext:
                await _upsert_fulltext(db, paper_id, "latex", markdown, sections)
            return {"markdown": markdown, "source": "latex", "sections": sections, "pdf_cached": pdf_path.exists()}

        pdf_bytes = pdf_path.read_bytes() if pdf_path.exists() else None
        if pdf_bytes is None:
            pdf_bytes = await _download_pdf(client, content_id, None)
            if pdf_bytes:
                _atomic_write_bytes(pdf_path, pdf_bytes)

        if pdf_bytes:
            full_text, sections = _extract_text_from_pdf_bytes(pdf_bytes)
            markdown = _markdown_from_sections(paper, "pdf", version, sections, full_text)
            _atomic_write_text(markdown_path, markdown)
            if update_fulltext:
                await _upsert_fulltext(db, paper_id, "pdf", markdown, sections)
            return {"markdown": markdown, "source": "pdf", "sections": sections, "pdf_cached": True}

    raise AIReadyPaperError(503, "Could not retrieve paper content from ar5iv, arXiv source, or PDF")


def _cache_hit_response(
    paper_id: str,
    version: str | None,
    paper: dict,
    markdown_path: Path,
    source: str,
) -> dict:
    content_id = _versioned_id(paper_id, version)
    return {
        "paper_id": paper_id,
        "version": version,
        "versioned_id": content_id,
        "paper": paper,
        "markdown": markdown_path.read_text(encoding="utf-8"),
        "source": source,
        "cached": True,
        "pdf_cached": _cache_path("pdf", content_id, ".pdf").exists(),
    }


async def get_ai_ready_paper(
    db: AsyncSession,
    raw_paper_id: str,
    *,
    on_cache_miss: Callable[[], Awaitable[None]] | None = None,
) -> dict:
    """Return the AI-ready paper.

    `on_cache_miss` is awaited only when the local cache cannot satisfy the
    request, before any expensive arXiv metadata fetch or content generation.
    Cache hits never invoke it. The callback may raise to abort generation
    (e.g. rate limiting).
    """

    paper_id = normalize_arxiv_id(raw_paper_id)
    requested_version = _requested_version(raw_paper_id)

    # Fast path: try the local cache using metadata we already have in the DB.
    # No arXiv API call, no rate limit, no lock.
    paper = await get_paper(db, paper_id)
    fast_version = requested_version or _version_from_paper(paper)
    if paper and fast_version:
        fast_markdown_path = _cache_path("markdown", _versioned_id(paper_id, fast_version), ".md")
        if fast_markdown_path.exists():
            source = await _cached_content_source(db, paper_id)
            return _cache_hit_response(paper_id, fast_version, paper, fast_markdown_path, source)

    # Cache miss path: rate-limit before doing anything expensive.
    if on_cache_miss is not None:
        await on_cache_miss()

    paper, version, update_fulltext = await _ensure_paper_metadata(db, paper_id, requested_version)
    paper_id = paper["id"]
    content_id = _versioned_id(paper_id, version)

    markdown_path = _cache_path("markdown", content_id, ".md")
    if markdown_path.exists():
        source = await _cached_content_source(db, paper_id)
        return _cache_hit_response(paper_id, version, paper, markdown_path, source)

    lock_token = await _acquire_generation_lock(content_id)
    try:
        if markdown_path.exists():
            source = await _cached_content_source(db, paper_id)
            return _cache_hit_response(paper_id, version, paper, markdown_path, source)

        generated = await _generate_markdown(db, paper, version, update_fulltext)
        return {
            "paper_id": paper_id,
            "version": version,
            "versioned_id": content_id,
            "paper": paper,
            "markdown": generated["markdown"],
            "source": generated["source"],
            "cached": False,
            "pdf_cached": generated["pdf_cached"],
        }
    finally:
        await _release_generation_lock(content_id, lock_token)
