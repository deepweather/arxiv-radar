from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, Collection, CollectionPaper, Paper, SavedPaper
from app.api.deps import get_current_user, get_optional_user

router = APIRouter()


class CollectionCreate(BaseModel):
    name: str
    description: str = ""
    is_public: bool = False


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


class PaperIdBody(BaseModel):
    paper_id: str
    note: str = ""


# --- Saved Papers (Reading List) — must be before /{collection_id} routes ---

@router.get("/saved/papers")
async def list_saved_papers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Paper)
        .join(SavedPaper, SavedPaper.paper_id == Paper.id)
        .where(SavedPaper.user_id == user.id)
        .order_by(SavedPaper.created_at.desc())
    )
    papers = result.scalars().all()
    return {
        "papers": [
            {
                "id": p.id, "title": p.title, "summary": p.summary,
                "authors": p.authors, "categories": p.categories,
                "pdf_url": p.pdf_url,
                "published_at": p.published_at.isoformat() if p.published_at else None,
            }
            for p in papers
        ]
    }


@router.post("/saved/papers", status_code=status.HTTP_201_CREATED)
async def save_paper(
    body: PaperIdBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(SavedPaper).where(SavedPaper.user_id == user.id, SavedPaper.paper_id == body.paper_id)
    )
    if existing.scalar_one_or_none():
        return {"detail": "Already saved"}
    db.add(SavedPaper(user_id=user.id, paper_id=body.paper_id))
    return {"detail": "Saved"}


@router.delete("/saved/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_paper(
    paper_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        sa_delete(SavedPaper).where(SavedPaper.user_id == user.id, SavedPaper.paper_id == paper_id)
    )


# --- Collections ---

@router.get("")
async def list_collections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Collection, func.count(CollectionPaper.paper_id).label("paper_count"))
        .outerjoin(CollectionPaper, CollectionPaper.collection_id == Collection.id)
        .where(Collection.user_id == user.id)
        .group_by(Collection.id)
        .order_by(Collection.created_at.desc())
    )
    return {
        "collections": [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "is_public": c.is_public,
                "paper_count": count,
                "created_at": c.created_at.isoformat(),
            }
            for c, count in result.all()
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CollectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    coll = Collection(user_id=user.id, name=body.name.strip(), description=body.description, is_public=body.is_public)
    db.add(coll)
    await db.flush()
    return {"id": str(coll.id), "name": coll.name, "description": coll.description, "is_public": coll.is_public}


@router.get("/{collection_id}")
async def get_collection(
    collection_id: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not coll.is_public and (not user or user.id != coll.user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    papers_result = await db.execute(
        select(Paper, CollectionPaper.note)
        .join(CollectionPaper, CollectionPaper.paper_id == Paper.id)
        .where(CollectionPaper.collection_id == coll.id)
        .order_by(CollectionPaper.created_at.desc())
    )
    return {
        "id": str(coll.id),
        "name": coll.name,
        "description": coll.description,
        "is_public": coll.is_public,
        "papers": [
            {
                "id": p.id, "title": p.title, "summary": p.summary,
                "authors": p.authors, "categories": p.categories,
                "pdf_url": p.pdf_url,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "note": note,
            }
            for p, note in papers_result.all()
        ],
    }


@router.patch("/{collection_id}")
async def update_collection(
    collection_id: str,
    body: CollectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id, Collection.user_id == user.id))
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    if body.name is not None:
        coll.name = body.name.strip()
    if body.description is not None:
        coll.description = body.description
    if body.is_public is not None:
        coll.is_public = body.is_public
    return {"detail": "Updated"}


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id, Collection.user_id == user.id))
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    await db.delete(coll)


@router.post("/{collection_id}/papers", status_code=status.HTTP_201_CREATED)
async def add_paper_to_collection(
    collection_id: str,
    body: PaperIdBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id, Collection.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Collection not found")

    existing = await db.execute(
        select(CollectionPaper).where(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == body.paper_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"detail": "Already in collection"}

    db.add(CollectionPaper(collection_id=collection_id, paper_id=body.paper_id, note=body.note))
    return {"detail": "Added"}


@router.delete("/{collection_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_paper_from_collection(
    collection_id: str,
    paper_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        sa_delete(CollectionPaper).where(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper_id,
        )
    )
