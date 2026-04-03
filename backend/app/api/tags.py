from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, Tag, PaperTag, Paper
from app.api.deps import get_current_user

router = APIRouter()


class TagCreate(BaseModel):
    name: str


class TagResponse(BaseModel):
    id: int
    name: str
    paper_count: int = 0


class PaperTagRequest(BaseModel):
    paper_id: str


@router.get("", response_model=list[TagResponse])
async def list_tags(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tag, func.count(PaperTag.paper_id).label("paper_count"))
        .outerjoin(PaperTag, PaperTag.tag_id == Tag.id)
        .where(Tag.user_id == user.id)
        .group_by(Tag.id)
        .order_by(Tag.name)
    )
    return [
        TagResponse(id=tag.id, name=tag.name, paper_count=count)
        for tag, count in result.all()
    ]


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    body: TagCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    name = body.name.strip()
    if not name or len(name) > 100:
        raise HTTPException(status_code=400, detail="Tag name must be 1-100 characters")

    existing = await db.execute(
        select(Tag).where(Tag.user_id == user.id, Tag.name == name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tag already exists")

    tag = Tag(user_id=user.id, name=name)
    db.add(tag)
    await db.flush()
    return TagResponse(id=tag.id, name=tag.name, paper_count=0)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tag).where(Tag.id == tag_id, Tag.user_id == user.id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.delete(tag)


@router.post("/{tag_id}/papers", status_code=status.HTTP_201_CREATED)
async def add_paper_to_tag(
    tag_id: int,
    body: PaperTagRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tag).where(Tag.id == tag_id, Tag.user_id == user.id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    paper = await db.execute(select(Paper).where(Paper.id == body.paper_id))
    if not paper.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Paper not found")

    existing = await db.execute(
        select(PaperTag).where(PaperTag.tag_id == tag_id, PaperTag.paper_id == body.paper_id)
    )
    if existing.scalar_one_or_none():
        return {"detail": "Already tagged"}

    db.add(PaperTag(tag_id=tag_id, paper_id=body.paper_id))
    return {"detail": "Paper tagged"}


@router.delete("/{tag_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_paper_from_tag(
    tag_id: int,
    paper_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tag).where(Tag.id == tag_id, Tag.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.execute(delete(PaperTag).where(PaperTag.tag_id == tag_id, PaperTag.paper_id == paper_id))


@router.get("/{tag_id}/papers")
async def list_tag_papers(
    tag_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tag).where(Tag.id == tag_id, Tag.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tag not found")

    papers_result = await db.execute(
        select(Paper)
        .join(PaperTag, PaperTag.paper_id == Paper.id)
        .where(PaperTag.tag_id == tag_id)
        .order_by(Paper.published_at.desc())
    )
    papers = papers_result.scalars().all()
    return {
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "summary": p.summary,
                "authors": p.authors,
                "categories": p.categories,
                "pdf_url": p.pdf_url,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in papers
        ]
    }
