from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.citations import get_citations

router = APIRouter()


@router.get("/trending")
async def trending_papers(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Papers most frequently tagged by users in the last N days."""
    sql = text("""
        SELECT p.id, p.title, p.summary, p.authors, p.categories,
               p.pdf_url, p.published_at, p.updated_at,
               COUNT(DISTINCT pt.tag_id) AS tag_count
        FROM papers p
        JOIN paper_tags pt ON pt.paper_id = p.id
        WHERE pt.created_at > NOW() - make_interval(days => :days)
        GROUP BY p.id
        ORDER BY tag_count DESC, p.published_at DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, {"days": days, "limit": limit})
    papers = []
    for row in result.fetchall():
        papers.append({
            "id": row.id,
            "title": row.title,
            "summary": row.summary,
            "authors": row.authors,
            "categories": row.categories,
            "pdf_url": row.pdf_url,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "tag_count": row.tag_count,
        })
    return {"papers": papers}


@router.get("/citations/{paper_id}")
async def paper_citations(paper_id: str):
    """Get citation graph data from Semantic Scholar."""
    data = await get_citations(paper_id)
    return data
