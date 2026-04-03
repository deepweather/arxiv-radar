"""Background worker — single async event loop running all periodic tasks sequentially."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_engine = None
_session_factory = None
_job_lock: asyncio.Lock | None = None


def _get_job_lock() -> asyncio.Lock:
    global _job_lock
    if _job_lock is None:
        _job_lock = asyncio.Lock()
    return _job_lock


def _get_session_factory():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False, pool_size=5)
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def run_ingest_and_embed():
    from app.services.arxiv_ingest import ingest_papers
    from app.services.embeddings import compute_embeddings

    async with _get_job_lock():
        factory = _get_session_factory()

        async with factory() as db:
            try:
                count = await ingest_papers(db)
                logger.info("Ingest finished: %d papers processed", count)
            except Exception:
                logger.exception("Ingest failed")

        async with factory() as db:
            try:
                count = await compute_embeddings(db)
                logger.info("Embedding finished: %d papers embedded", count)
            except Exception:
                logger.exception("Embedding failed")


async def run_citation_fetch():
    from app.services.citations import fetch_citations_batch
    from sqlalchemy import text

    async with _get_job_lock():
        factory = _get_session_factory()

        async with factory() as db:
            try:
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

        async with factory() as db:
            try:
                count = await fetch_citations_batch(db, batch_size=50)
                logger.info("Citation fetch finished: %d papers processed", count)
            except Exception:
                logger.exception("Citation fetch failed")


async def run_startup():
    """Run all startup tasks sequentially to avoid connection pool conflicts."""
    logger.info("Running startup tasks...")
    await run_ingest_and_embed()
    await run_citation_fetch()
    logger.info("Startup tasks complete")


async def main():
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        run_ingest_and_embed,
        "interval",
        minutes=settings.arxiv_ingest_interval_minutes,
        id="ingest_and_embed",
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        run_citation_fetch,
        "interval",
        minutes=10,
        id="citation_fetch",
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        run_startup,
        "date",
        id="startup",
    )

    logger.info(
        "Worker started — ingest every %d minutes, citation fetch every 10 minutes, categories: %s",
        settings.arxiv_ingest_interval_minutes,
        settings.arxiv_categories,
    )

    scheduler.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker shutting down")
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
