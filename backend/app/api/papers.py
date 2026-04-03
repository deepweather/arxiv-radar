import hashlib
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_optional_user
from app.services.search import hybrid_search, list_papers, get_paper, count_papers
from app.services.recommender import similar_papers, papers_by_authors

router = APIRouter()


async def get_user_tags_for_papers(
    db: AsyncSession, user_id: str, paper_ids: list[str]
) -> dict[str, list[dict]]:
    """Fetch user's tags for a list of papers. Returns dict mapping paper_id to list of tag objects."""
    if not paper_ids:
        return {}
    
    sql = sa_text("""
        SELECT pt.paper_id, t.id, t.name
        FROM paper_tags pt
        JOIN tags t ON t.id = pt.tag_id
        WHERE t.user_id = CAST(:user_id AS uuid)
        AND pt.paper_id = ANY(:paper_ids)
    """)
    result = await db.execute(sql, {"user_id": user_id, "paper_ids": paper_ids})
    
    tags_map: dict[str, list[dict]] = defaultdict(list)
    for row in result.fetchall():
        tags_map[row.paper_id].append({"id": row.id, "name": row.name})
    
    return tags_map


@router.get("")
async def get_papers(
    q: str | None = Query(None, description="Search query"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    days: int | None = Query(None, ge=1, description="Filter to last N days"),
    categories: str | None = Query(None, description="Comma-separated categories to filter"),
    sort: str | None = Query(None, description="Sort order: relevance, newest, oldest, random"),
    exclude_tagged: bool = Query(False, description="Exclude papers user has tagged"),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    cats = [c.strip() for c in categories.split(",")] if categories else None
    user_id = str(user.id) if user and exclude_tagged else None
    if q:
        papers = await hybrid_search(db, query=q, limit=limit, offset=offset, days=days, categories=cats, sort=sort, user_id=user_id)
    else:
        papers = await list_papers(db, limit=limit, offset=offset, days=days, categories=cats, sort=sort, user_id=user_id)
    
    # Add user tags to papers if user is logged in
    if user:
        paper_ids = [p["id"] for p in papers]
        tags_map = await get_user_tags_for_papers(db, str(user.id), paper_ids)
        for paper in papers:
            paper["user_tags"] = tags_map.get(paper["id"], [])
    
    return {"papers": papers, "page_size": len(papers)}


@router.get("/count")
async def paper_count(db: AsyncSession = Depends(get_db)):
    total = await count_papers(db)
    return {"count": total}


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get database statistics for transparency."""
    stats_sql = sa_text("""
        SELECT 
            COUNT(*) as total_papers,
            MIN(published_at) as earliest_date,
            MAX(published_at) as latest_date,
            COUNT(*) FILTER (WHERE published_at > NOW() - INTERVAL '24 hours') as papers_last_24h,
            COUNT(*) FILTER (WHERE published_at > NOW() - INTERVAL '7 days') as papers_last_7d,
            COUNT(*) FILTER (WHERE published_at > NOW() - INTERVAL '30 days') as papers_last_30d,
            COUNT(*) FILTER (WHERE embedding IS NOT NULL) as papers_with_embeddings
        FROM papers
    """)
    result = await db.execute(stats_sql)
    row = result.fetchone()
    
    users_sql = sa_text("SELECT COUNT(*) FROM users")
    users_result = await db.execute(users_sql)
    total_users = users_result.scalar() or 0
    
    tags_sql = sa_text("SELECT COUNT(*) FROM tags")
    tags_result = await db.execute(tags_sql)
    total_tags = tags_result.scalar() or 0
    
    paper_tags_sql = sa_text("SELECT COUNT(*) FROM paper_tags")
    paper_tags_result = await db.execute(paper_tags_sql)
    total_paper_tags = paper_tags_result.scalar() or 0
    
    return {
        "total_papers": row.total_papers,
        "earliest_date": row.earliest_date.isoformat() if row.earliest_date else None,
        "latest_date": row.latest_date.isoformat() if row.latest_date else None,
        "papers_last_24h": row.papers_last_24h,
        "papers_last_7d": row.papers_last_7d,
        "papers_last_30d": row.papers_last_30d,
        "papers_with_embeddings": row.papers_with_embeddings,
        "total_users": total_users,
        "total_tags": total_tags,
        "total_paper_tags": total_paper_tags,
    }


@router.get("/{paper_id}")
async def get_paper_detail(paper_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    paper = await get_paper(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    session_hash = hashlib.sha256(f"{client_ip}:{request.headers.get('user-agent', '')}".encode()).hexdigest()[:16]
    await db.execute(
        sa_text("INSERT INTO paper_views (paper_id, session_hash) VALUES (:pid, :sh)"),
        {"pid": paper_id, "sh": session_hash},
    )
    await db.flush()

    return paper


@router.get("/{paper_id}/by-authors")
async def get_papers_by_authors(
    paper_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    paper = await get_paper(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    author_names = [a["name"] for a in paper.get("authors", [])[:3]]
    papers = await papers_by_authors(db, author_names, exclude_paper_id=paper_id, limit=limit)
    return {"papers": papers}


@router.get("/{paper_id}/similar")
async def get_similar_papers(
    paper_id: str,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    papers = await similar_papers(db, paper_id, limit=limit)
    return {"papers": papers}
