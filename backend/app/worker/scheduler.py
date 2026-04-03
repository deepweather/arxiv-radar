"""Background worker — runs periodic ingest, embedding, and citation fetch tasks."""

import asyncio
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False, pool_size=5)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _run_ingest_and_embed():
    from app.services.arxiv_ingest import ingest_papers
    from app.services.embeddings import compute_embeddings

    async with session_factory() as db:
        try:
            count = await ingest_papers(db)
            logger.info("Ingest finished: %d papers processed", count)
        except Exception:
            logger.exception("Ingest failed")

    async with session_factory() as db:
        try:
            count = await compute_embeddings(db)
            logger.info("Embedding finished: %d papers embedded", count)
        except Exception:
            logger.exception("Embedding failed")


async def _run_citation_fetch():
    from app.services.citations import fetch_citations_batch
    from sqlalchemy import text

    async with session_factory() as db:
        try:
            # First, queue any papers that aren't in the cache yet
            await db.execute(text("""
                INSERT INTO citation_cache (paper_id, status, data)
                SELECT p.id, 'pending', '{}'::jsonb
                FROM papers p
                LEFT JOIN citation_cache cc ON cc.paper_id = p.id
                WHERE cc.paper_id IS NULL
            """))
            await db.commit()
        except Exception:
            logger.exception("Citation queue seeding failed")

    async with session_factory() as db:
        try:
            count = await fetch_citations_batch(db, batch_size=50)
            logger.info("Citation fetch finished: %d papers processed", count)
        except Exception:
            logger.exception("Citation fetch failed")


def run_ingest_and_embed():
    asyncio.run(_run_ingest_and_embed())


def run_citation_fetch():
    asyncio.run(_run_citation_fetch())


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    scheduler.add_job(
        run_ingest_and_embed,
        "interval",
        minutes=settings.arxiv_ingest_interval_minutes,
        id="ingest_and_embed",
        max_instances=1,
    )

    scheduler.add_job(
        run_citation_fetch,
        "interval",
        minutes=10,
        id="citation_fetch",
        max_instances=1,
    )

    # Run once on startup
    scheduler.add_job(
        run_ingest_and_embed,
        "date",
        id="ingest_and_embed_startup",
    )

    scheduler.add_job(
        run_citation_fetch,
        "date",
        id="citation_fetch_startup",
    )

    logger.info(
        "Worker started — ingest every %d minutes, citation fetch every 10 minutes, categories: %s",
        settings.arxiv_ingest_interval_minutes,
        settings.arxiv_categories,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker shutting down")
