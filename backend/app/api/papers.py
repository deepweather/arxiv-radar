import hashlib

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.search import hybrid_search, list_papers, get_paper, count_papers
from app.services.recommender import similar_papers, papers_by_authors

router = APIRouter()


@router.get("")
async def get_papers(
    q: str | None = Query(None, description="Search query"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    days: int | None = Query(None, ge=1, description="Filter to last N days"),
    categories: str | None = Query(None, description="Comma-separated categories to filter"),
    db: AsyncSession = Depends(get_db),
):
    cats = [c.strip() for c in categories.split(",")] if categories else None
    if q:
        papers = await hybrid_search(db, query=q, limit=limit, offset=offset, days=days, categories=cats)
    else:
        papers = await list_papers(db, limit=limit, offset=offset, days=days, categories=cats)
    return {"papers": papers, "page_size": len(papers)}


@router.get("/count")
async def paper_count(db: AsyncSession = Depends(get_db)):
    total = await count_papers(db)
    return {"count": total}


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
