from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.citations import get_citations

router = APIRouter()


@router.get("/citations/{paper_id}")
async def paper_citations(paper_id: str, db: AsyncSession = Depends(get_db)):
    """Get citation data from the local database (populated by background worker)."""
    return await get_citations(db, paper_id)
