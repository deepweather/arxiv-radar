"""Compute sentence-transformer embeddings for papers missing them."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import HNSW_M, HNSW_EF_CONSTRUCTION

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model, cache_folder=settings.model_cache_dir)
        logger.info("Model loaded")
    return _model


async def compute_embeddings(db: AsyncSession, batch_size: int = 128, max_papers: int = 0) -> int:
    """Compute embeddings for papers that don't have them yet. Returns count of papers embedded.
    
    Args:
        batch_size: papers per encode() call (GPU/CPU chunk)
        max_papers: total papers to process (0 = all pending)
    """
    limit = max_papers if max_papers > 0 else 100_000
    result = await db.execute(
        text("SELECT id, title, summary FROM papers WHERE embedding IS NULL ORDER BY published_at DESC LIMIT :limit"),
        {"limit": limit},
    )
    rows = result.fetchall()
    if not rows:
        logger.info("No papers need embedding")
        return 0

    logger.info("Computing embeddings for %d papers", len(rows))
    model = _get_model()

    update_sql = text("UPDATE papers SET embedding = :emb WHERE id = :id")
    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        texts = [f"{r.title} {r.summary}" for r in chunk]
        embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

        for r, emb in zip(chunk, embeddings):
            await db.execute(update_sql, {"id": r.id, "emb": str(emb.tolist())})

        total += len(chunk)
        if total % (batch_size * 4) == 0:
            await db.commit()
        logger.info("Embedded %d/%d papers", total, len(rows))

    await db.commit()
    logger.info("Embedding complete: %d papers processed", total)
    return total


async def ensure_hnsw_index(db: AsyncSession) -> None:
    """Create the HNSW index if it doesn't exist. Call after bulk embedding."""
    logger.info("Creating HNSW index (this may take a few minutes)...")
    await db.execute(text(
        f"CREATE INDEX IF NOT EXISTS ix_papers_embedding_hnsw "
        f"ON papers USING hnsw (embedding vector_cosine_ops) "
        f"WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION})"
    ))
    await db.commit()
    logger.info("HNSW index ready")
