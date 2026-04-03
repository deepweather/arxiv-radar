from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, Tag
from app.api.deps import get_current_user
from app.services.recommender import recommend_for_tag, recommend_for_user
from app.services.classifier_recommender import recommend_with_classifier_and_explanation

router = APIRouter()


@router.get("/for-you")
async def for_you(
    limit: int = Query(25, ge=1, le=100),
    days: int = Query(7, ge=1),
    use_classifier: bool = Query(True, description="Use ML classifier (better) vs centroid (faster)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if use_classifier:
        papers = await recommend_with_classifier_and_explanation(db, str(user.id), limit=limit, days=days)
        if papers:
            return {"papers": papers, "method": "classifier"}
    
    papers = await recommend_for_user(db, str(user.id), limit=limit, days=days)
    return {"papers": papers, "method": "centroid"}


@router.get("/tag/{tag_id}")
async def by_tag(
    tag_id: int,
    limit: int = Query(25, ge=1, le=100),
    days: int | None = Query(None, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tag).where(Tag.id == tag_id, Tag.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tag not found")
    papers = await recommend_for_tag(db, tag_id, limit=limit, days=days)
    return {"papers": papers}
