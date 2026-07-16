"""MCP server exposing arxiv-radar tools for AI agents.

Run with:  python -m app.mcp_server
Or:        mcp run app/mcp_server.py
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    session_factory: async_sessionmaker


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    engine = create_async_engine(settings.database_url, echo=False, pool_size=5, max_overflow=5)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield AppContext(session_factory=factory)
    finally:
        await engine.dispose()


mcp = FastMCP(
    "arxiv-radar",
    lifespan=app_lifespan,
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8811")),
)


def _get_factory(ctx: Context) -> async_sessionmaker:
    return ctx.request_context.lifespan_context.session_factory


def _format_paper(p: dict) -> str:
    """Format a paper dict as readable text for agents."""
    authors = p.get("authors", [])
    author_str = ", ".join(a.get("name", "") for a in authors[:5]) if isinstance(authors, list) else str(authors)
    if isinstance(authors, list) and len(authors) > 5:
        author_str += f" (+{len(authors) - 5} more)"

    cats = ", ".join(p.get("categories", []))
    pid = p.get("id", "N/A")
    lines = [
        f"**{p.get('title', 'Untitled')}**",
        f"arXiv ID: {pid}",
        f"Authors: {author_str}",
        f"Categories: {cats}",
        f"Published: {p.get('published_at', 'N/A')}",
        f"PDF: {p.get('pdf_url', 'N/A')}",
        f"HTML: https://ar5iv.labs.arxiv.org/html/{pid}",
        f"Abstract page: https://arxiv.org/abs/{pid}",
    ]
    if p.get("score"):
        lines.append(f"Relevance score: {p['score']}")
    if p.get("similarity"):
        lines.append(f"Similarity: {p['similarity']}")
    lines.append(f"\nAbstract: {p.get('summary', 'N/A')}")
    return "\n".join(lines)



# ── Tools ──────────────────────────────────────────────────────────────


@mcp.tool()
async def search_papers(
    query: str,
    limit: int = 10,
    categories: str | None = None,
    days: int | None = None,
    sort: str | None = None,
    ctx: Context = None,
) -> str:
    """Search arXiv papers by semantic similarity to a natural language query.

    Returns papers ranked by hybrid semantic + full-text search relevance.

    Args:
        query: Natural language search query (e.g. "transformer architectures for protein folding")
        limit: Maximum number of results to return (default 10, max 50)
        categories: Comma-separated arXiv category filter (e.g. "cs.LG,cs.AI")
        days: Only include papers published in the last N days
        sort: Sort order — "relevance" (default), "newest", or "oldest"
    """
    from app.services.search import hybrid_search

    limit = min(limit, 50)
    cat_list = [c.strip() for c in categories.split(",")] if categories else None

    factory = _get_factory(ctx)
    async with factory() as db:
        results = await hybrid_search(
            db, query, limit=limit, categories=cat_list, days=days, sort=sort,
        )

    if not results:
        return "No papers found matching your query."

    parts = [f"Found {len(results)} papers:\n"]
    for i, p in enumerate(results, 1):
        parts.append(f"### {i}. {_format_paper(p)}\n")
    return "\n".join(parts)


@mcp.tool()
async def get_paper(paper_id: str, ctx: Context = None) -> str:
    """Get detailed metadata for a single arXiv paper by its ID.

    Args:
        paper_id: The arXiv paper ID (e.g. "2301.12345" or "2301.12345v2")
    """
    from app.services.search import get_paper as _get_paper

    paper_id = paper_id.strip()
    if "v" in paper_id and paper_id[-1].isdigit():
        paper_id = paper_id.split("v")[0]

    factory = _get_factory(ctx)
    async with factory() as db:
        paper = await _get_paper(db, paper_id)

    if not paper:
        return f"Paper '{paper_id}' not found in the database."

    return _format_paper(paper)


@mcp.tool()
async def get_ai_ready_paper(paper_id: str, ctx: Context = None) -> str:
    """Get the full paper as clean markdown for AI assistants.

    Args:
        paper_id: The arXiv paper ID (e.g. "2303.08774" or "2303.08774v1")
    """
    from app.services.ai_ready_papers import AIReadyPaperError, get_ai_ready_paper as _get_ai_ready_paper

    factory = _get_factory(ctx)
    async with factory() as db:
        try:
            result = await _get_ai_ready_paper(db, paper_id)
            await db.commit()
        except AIReadyPaperError as exc:
            return f"Could not get AI-ready paper '{paper_id}': {exc.detail}"

    header = (
        f"AI-ready markdown for {result['versioned_id']}\n"
        f"Source: {result['source']}\n"
        f"Cached: {result['cached']}\n"
        f"PDF cached: {result['pdf_cached']}\n"
    )
    return f"{header}\n{result['markdown']}"


@mcp.tool()
async def list_recent_papers(
    limit: int = 20,
    categories: str | None = None,
    days: int = 7,
    sort: str = "newest",
    ctx: Context = None,
) -> str:
    """List recently published arXiv papers.

    Args:
        limit: Maximum number of papers to return (default 20, max 50)
        categories: Comma-separated arXiv category filter (e.g. "cs.LG,cs.CL")
        days: Only include papers from the last N days (default 7)
        sort: Sort order — "newest" (default), "oldest", or "random"
    """
    from app.services.search import list_papers

    limit = min(limit, 50)
    cat_list = [c.strip() for c in categories.split(",")] if categories else None

    factory = _get_factory(ctx)
    async with factory() as db:
        results = await list_papers(db, limit=limit, categories=cat_list, days=days, sort=sort)

    if not results:
        return "No recent papers found matching the criteria."

    parts = [f"Found {len(results)} recent papers (last {days} days):\n"]
    for i, p in enumerate(results, 1):
        parts.append(f"### {i}. {_format_paper(p)}\n")
    return "\n".join(parts)


@mcp.tool()
async def get_similar_papers(paper_id: str, limit: int = 10, ctx: Context = None) -> str:
    """Find papers similar to a given paper using vector similarity.

    Args:
        paper_id: The arXiv paper ID to find similar papers for
        limit: Maximum number of similar papers (default 10, max 30)
    """
    from app.services.recommender import similar_papers

    paper_id = paper_id.strip().split("v")[0] if "v" in paper_id else paper_id.strip()
    limit = min(limit, 30)

    factory = _get_factory(ctx)
    async with factory() as db:
        results = await similar_papers(db, paper_id, limit=limit)

    if not results:
        return f"No similar papers found for '{paper_id}'. The paper may not exist or may not have an embedding yet."

    parts = [f"Papers similar to {paper_id}:\n"]
    for i, p in enumerate(results, 1):
        parts.append(f"### {i}. {_format_paper(p)}\n")
    return "\n".join(parts)


@mcp.tool()
async def list_collections(
    sort: str = "popular",
    limit: int = 20,
    ctx: Context = None,
) -> str:
    """List public curated paper collections.

    Browse collections of papers grouped by research topic (e.g. "World Models",
    "AI Weather Models", "Reasoning & Thinking Models").

    Args:
        sort: Sort order — "popular" (default, by total views), "trending" (by recent views), or "recent" (newest first)
        limit: Maximum number of collections to return (default 20, max 50)
    """
    from sqlalchemy import select, func
    from app.db.models import Collection, CollectionPaper, User

    limit = min(limit, 50)
    factory = _get_factory(ctx)
    async with factory() as db:
        paper_count_sq = (
            select(
                CollectionPaper.collection_id,
                func.count().label("paper_count"),
            )
            .group_by(CollectionPaper.collection_id)
            .subquery()
        )

        q = (
            select(
                Collection,
                User.email,
                func.coalesce(paper_count_sq.c.paper_count, 0).label("paper_count"),
            )
            .join(User, User.id == Collection.user_id)
            .outerjoin(paper_count_sq, paper_count_sq.c.collection_id == Collection.id)
            .where(Collection.is_public.is_(True))
        )

        if sort == "recent":
            q = q.order_by(Collection.created_at.desc())
        else:
            q = q.order_by(func.coalesce(paper_count_sq.c.paper_count, 0).desc())

        q = q.limit(limit)
        result = await db.execute(q)
        rows = result.all()

    if not rows:
        return "No public collections found."

    parts = [f"Found {len(rows)} public collections:\n"]
    for i, (coll, email, paper_count) in enumerate(rows, 1):
        parts.append(
            f"### {i}. **{coll.name}**\n"
            f"ID: {coll.id}\n"
            f"Papers: {paper_count}\n"
            f"Description: {coll.description or 'No description'}\n"
            f"URL: https://arxivradar.com/collections/{coll.id}\n"
        )
    return "\n".join(parts)


@mcp.tool()
async def get_collection(collection_id: str, ctx: Context = None) -> str:
    """Get a specific paper collection with all its papers.

    Returns the collection metadata and full details of every paper in it.

    Args:
        collection_id: The collection UUID (from list_collections)
    """
    from sqlalchemy import select, func
    from app.db.models import Collection, CollectionPaper, CollectionView, Paper, User

    factory = _get_factory(ctx)
    async with factory() as db:
        result = await db.execute(
            select(Collection).where(Collection.id == collection_id.strip())
        )
        coll = result.scalar_one_or_none()

        if not coll:
            return f"Collection '{collection_id}' not found."
        if not coll.is_public:
            return "This collection is private."

        owner_result = await db.execute(select(User.email).where(User.id == coll.user_id))
        owner_email = owner_result.scalar_one()

        papers_result = await db.execute(
            select(Paper, CollectionPaper.note)
            .join(CollectionPaper, CollectionPaper.paper_id == Paper.id)
            .where(CollectionPaper.collection_id == coll.id)
            .order_by(CollectionPaper.created_at.desc())
        )
        papers = papers_result.all()

        view_count_result = await db.execute(
            select(func.count()).select_from(CollectionView).where(CollectionView.collection_id == coll.id)
        )
        view_count = view_count_result.scalar() or 0

    header = (
        f"**{coll.name}**\n"
        f"Description: {coll.description or 'No description'}\n"
        f"Owner: {owner_email.split('@')[0]}\n"
        f"Papers: {len(papers)} | Views: {view_count}\n"
        f"URL: https://arxivradar.com/collections/{coll.id}\n"
    )

    if not papers:
        return header + "\nNo papers in this collection yet."

    parts = [header, f"\n{'─' * 40}\n"]
    for i, (p, note) in enumerate(papers, 1):
        paper_dict = {
            "id": p.id, "title": p.title, "summary": p.summary,
            "authors": p.authors, "categories": p.categories,
            "pdf_url": p.pdf_url,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        parts.append(f"### {i}. {_format_paper(paper_dict)}\n")
    return "\n".join(parts)


# ── HTTP app (Streamable HTTP + legacy SSE, both CORS-enabled) ──────────
#
# Web-based MCP clients require:
#   1. the Streamable HTTP transport (SSE alone is the deprecated transport),
#   2. CORS headers so a browser origin can reach the endpoint,
#   3. no origin/host rejection from the transport's DNS-rebinding guard.
#
# Desktop clients (e.g. via mcp-remote) still work against the legacy SSE
# endpoint, so we mount both on one ASGI app. Paths are aligned with the
# public `/mcp` prefix so the reverse proxy can forward them verbatim:
#   - Streamable HTTP : POST /mcp
#   - Legacy SSE      : GET  /mcp/sse   +  POST /mcp/messages/


def _cors_origins() -> list[str]:
    raw = os.getenv("MCP_CORS_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def build_http_app():
    """Build the combined Streamable HTTP + SSE Starlette app with CORS."""
    from starlette.middleware.cors import CORSMiddleware

    # Align transport paths with the public `/mcp` prefix so nginx forwards
    # `/mcp*` unchanged (no path rewriting / sub_filter hacks needed).
    mcp.settings.streamable_http_path = "/mcp"
    mcp.settings.sse_path = "/mcp/sse"
    mcp.settings.message_path = "/mcp/messages/"

    # This is a public, unauthenticated, read-only server sitting behind a
    # reverse proxy. The DNS-rebinding guard would otherwise 400 any request
    # whose Origin/Host isn't localhost; disable it and rely on CORS instead.
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )

    # streamable_http_app() carries the session-manager lifespan.
    app = mcp.streamable_http_app()

    # Fold the legacy SSE routes onto the same app for desktop-client back-compat.
    sse_routes = mcp.sse_app().router.routes
    app.router.routes.extend(sse_routes)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
        max_age=86400,
    )
    return app


# Module-level app so it can be served with `uvicorn app.mcp_server:app`.
app = build_http_app()


# ── Entry point ────────────────────────────────────────────────────────

def main():
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport in ("http", "streamable-http", "sse"):
        import uvicorn

        uvicorn.run(app, host=mcp.settings.host, port=mcp.settings.port)
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
