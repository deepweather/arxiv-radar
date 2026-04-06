import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import (
    User,
    Collection,
    CollectionPaper,
    CollectionView,
    Paper,
    SavedPaper,
)
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


def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


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


# --- Public Collections (discovery) — must be before /{collection_id} ---

@router.get("/public")
async def list_public_collections(
    sort: str = Query("trending", description="trending, popular, or recent"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    views_7d = (
        select(
            CollectionView.collection_id,
            func.count().label("views_7d"),
        )
        .where(CollectionView.viewed_at >= seven_days_ago)
        .group_by(CollectionView.collection_id)
        .subquery()
    )

    views_total = (
        select(
            CollectionView.collection_id,
            func.count().label("views_total"),
        )
        .group_by(CollectionView.collection_id)
        .subquery()
    )

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
            func.coalesce(views_total.c.views_total, 0).label("view_count"),
            func.coalesce(views_7d.c.views_7d, 0).label("views_7d"),
        )
        .join(User, User.id == Collection.user_id)
        .outerjoin(paper_count_sq, paper_count_sq.c.collection_id == Collection.id)
        .outerjoin(views_total, views_total.c.collection_id == Collection.id)
        .outerjoin(views_7d, views_7d.c.collection_id == Collection.id)
        .where(Collection.is_public.is_(True))
    )

    if sort == "trending":
        q = q.order_by(func.coalesce(views_7d.c.views_7d, 0).desc(), Collection.created_at.desc())
    elif sort == "popular":
        q = q.order_by(func.coalesce(views_total.c.views_total, 0).desc(), func.coalesce(paper_count_sq.c.paper_count, 0).desc())
    else:
        q = q.order_by(Collection.created_at.desc())

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)

    collections = []
    for coll, email, paper_count, view_count, v7d in result.all():
        collections.append({
            "id": str(coll.id),
            "name": coll.name,
            "description": coll.description,
            "is_public": True,
            "share_slug": coll.share_slug,
            "paper_count": paper_count,
            "view_count": view_count,
            "owner_name": email.split("@")[0],
            "created_at": coll.created_at.isoformat(),
        })

    return {"collections": collections}


# --- Slug-based lookup — must be before /{collection_id} ---

@router.get("/by-slug/{slug}")
async def get_collection_by_slug(
    slug: str,
    request: Request,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Collection).where(Collection.share_slug == slug))
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not coll.is_public and (not user or user.id != coll.user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return await _build_collection_response(coll, request, user, db)


# --- Collections CRUD ---

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
                "share_slug": c.share_slug,
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
    return {
        "id": str(coll.id),
        "name": coll.name,
        "description": coll.description,
        "is_public": coll.is_public,
        "share_slug": coll.share_slug,
    }


@router.get("/{collection_id}/og", response_class=HTMLResponse)
async def get_collection_og(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return minimal HTML with Open Graph meta tags for social media crawlers."""
    result = await db.execute(
        select(Collection, User.email)
        .join(User, User.id == Collection.user_id)
        .where(Collection.id == collection_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Collection not found")

    coll, email = row
    if not coll.is_public:
        raise HTTPException(status_code=404, detail="Collection not found")

    paper_count_result = await db.execute(
        select(func.count()).select_from(CollectionPaper).where(CollectionPaper.collection_id == coll.id)
    )
    paper_count = paper_count_result.scalar() or 0

    title = _escape_html(coll.name)
    owner = _escape_html(email.split("@")[0])
    desc_raw = coll.description or f"A collection of {paper_count} papers"
    description = _escape_html((desc_raw[:197] + "...") if len(desc_raw) > 200 else desc_raw)
    url = f"https://arxivradar.com/collections/{collection_id}"

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>{title} by {owner} - arxiv radar</title>
<meta name="description" content="{description}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{description} | {paper_count} papers by {owner}"/>
<meta property="og:url" content="{url}"/>
<meta property="og:type" content="website"/>
<meta property="og:site_name" content="arxiv radar"/>
<meta name="twitter:card" content="summary"/>
<meta name="twitter:title" content="{title}"/>
<meta name="twitter:description" content="{description}"/>
<meta http-equiv="refresh" content="0;url={url}"/>
</head><body><p>Redirecting to <a href="{url}">{title}</a></p></body></html>"""
    return HTMLResponse(content=html)


@router.get("/{collection_id}")
async def get_collection(
    collection_id: str,
    request: Request,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not coll.is_public and (not user or user.id != coll.user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return await _build_collection_response(coll, request, user, db)


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


# --- Helpers ---

async def _build_collection_response(
    coll: Collection,
    request: Request,
    user: User | None,
    db: AsyncSession,
) -> dict:
    """Build the enriched collection detail response with owner info, view count, and view tracking."""
    # Fetch owner email
    owner_result = await db.execute(select(User.email).where(User.id == coll.user_id))
    owner_email = owner_result.scalar_one()

    # Paper list
    papers_result = await db.execute(
        select(Paper, CollectionPaper.note)
        .join(CollectionPaper, CollectionPaper.paper_id == Paper.id)
        .where(CollectionPaper.collection_id == coll.id)
        .order_by(CollectionPaper.created_at.desc())
    )

    # View count
    view_count_result = await db.execute(
        select(func.count()).select_from(CollectionView).where(CollectionView.collection_id == coll.id)
    )
    view_count = view_count_result.scalar() or 0

    # Track view (anonymous, session-based)
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    session_hash = hashlib.sha256(f"{client_ip}:{request.headers.get('user-agent', '')}".encode()).hexdigest()[:16]
    db.add(CollectionView(collection_id=coll.id, session_hash=session_hash))
    await db.flush()

    is_owner = user is not None and user.id == coll.user_id

    return {
        "id": str(coll.id),
        "name": coll.name,
        "description": coll.description,
        "is_public": coll.is_public,
        "share_slug": coll.share_slug,
        "owner_name": owner_email.split("@")[0],
        "is_owner": is_owner,
        "view_count": view_count,
        "created_at": coll.created_at.isoformat(),
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
