"""Batch PDF download service for public collections."""

import asyncio
import io
import logging
import random
import re
import zipfile
from collections.abc import AsyncIterator

import httpx

from app.db.models import Paper

logger = logging.getLogger(__name__)

MAX_PAPERS = 50
MAX_TOTAL_BYTES = 500 * 1024 * 1024
MAX_CONCURRENT = 4
FILENAME_MAX = 80
USER_AGENT = "arxiv-radar/1.0 (+https://arxivradar.com)"

_NON_SAFE = re.compile(r"[^A-Za-z0-9._-]")


class _Buffer(io.RawIOBase):
    def __init__(self) -> None:
        self._data = bytearray()

    def writable(self) -> bool:
        return True

    def write(self, b: bytes | bytearray) -> int:
        self._data.extend(b)
        return len(b)

    def take(self) -> bytes:
        out = bytes(self._data)
        self._data.clear()
        return out


def sanitize_filename(s: str, max_len: int = FILENAME_MAX) -> str:
    """Collapse unsafe characters to '_', trim, and cap length."""
    if not s or not s.strip():
        return ""
    result = _NON_SAFE.sub("_", s.strip())
    return result[:max_len]


async def _fetch_pdf(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    paper: Paper,
) -> tuple[Paper, bytes | None, str | None]:
    """Fetch one PDF with up to 3 retries on transient errors.

    Returns (paper, pdf_bytes, error_reason).
    """
    assert paper.pdf_url is not None  # caller guarantees this

    async with sem:
        last_reason: str = "network_error"
        for attempt in range(3):
            try:
                resp = await client.get(paper.pdf_url)
                if resp.status_code == 200:
                    return paper, resp.content, None
                if resp.status_code == 404:
                    return paper, None, "http_404"
                if resp.status_code in (429, 503):
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt + random.uniform(0, 0.5)
                    last_reason = f"http_{resp.status_code}"
                    if attempt < 2:
                        await asyncio.sleep(delay)
                    continue
                last_reason = f"http_{resp.status_code}"
            except httpx.TimeoutException:
                last_reason = "timeout"
                if attempt < 2:
                    await asyncio.sleep(2**attempt + random.uniform(0, 0.5))
            except httpx.RequestError:
                last_reason = "network_error"
                if attempt < 2:
                    await asyncio.sleep(2**attempt + random.uniform(0, 0.5))

        return paper, None, last_reason


async def stream_collection_zip(papers: list[Paper]) -> AsyncIterator[bytes]:
    """Async generator that streams a ZIP archive of arXiv PDFs.

    Caller is responsible for filtering out papers without pdf_url and
    capping the list at MAX_PAPERS.
    """
    buf = _Buffer()
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10, read=60, write=10, pool=10),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        futures = [asyncio.ensure_future(_fetch_pdf(client, sem, p)) for p in papers]

        ok_entries: dict[str, str] = {}   # arxiv_id → arcname
        failed_entries: dict[str, str] = {}  # arxiv_id → reason
        total_bytes = 0
        size_limit_hit = False

        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED) as zf:
            for coro in asyncio.as_completed(futures):
                paper, pdf_bytes, reason = await coro

                if reason is not None:
                    failed_entries[paper.id] = reason
                    continue

                assert pdf_bytes is not None
                if size_limit_hit or total_bytes + len(pdf_bytes) > MAX_TOTAL_BYTES:
                    failed_entries[paper.id] = "size_limit"
                    size_limit_hit = True
                    continue

                safe_title = sanitize_filename(paper.title or "")
                arcname = f"{paper.id}-{safe_title}.pdf" if safe_title else f"{paper.id}.pdf"

                zf.writestr(arcname, pdf_bytes)
                ok_entries[paper.id] = arcname
                total_bytes += len(pdf_bytes)
                chunk = buf.take()
                if chunk:
                    yield chunk

            if not ok_entries:
                raise RuntimeError("All PDF fetches failed — no entries written to archive")

            manifest_lines = [
                "arxiv-radar collection download manifest",
                f"papers_requested: {len(papers)}",
                f"papers_ok: {len(ok_entries)}",
                f"papers_failed: {len(failed_entries)}",
                "",
                "ok:",
            ]
            for arxiv_id, arcname in sorted(ok_entries.items()):
                manifest_lines.append(f"  {arxiv_id} -> {arcname}")
            manifest_lines.append("")
            manifest_lines.append("failed:")
            for arxiv_id, reason in sorted(failed_entries.items()):
                manifest_lines.append(f"  {arxiv_id}: {reason}")

            zf.writestr("MANIFEST.txt", "\n".join(manifest_lines) + "\n")

    final_chunk = buf.take()
    if final_chunk:
        yield final_chunk
