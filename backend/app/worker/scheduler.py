"""Background worker — runs periodic ingest and embedding tasks via APScheduler."""

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


def run_ingest_and_embed():
    asyncio.run(_run_ingest_and_embed())


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    scheduler.add_job(
        run_ingest_and_embed,
        "interval",
        minutes=settings.arxiv_ingest_interval_minutes,
        id="ingest_and_embed",
        max_instances=1,
    )

    # Also run once on startup after a short delay
    scheduler.add_job(
        run_ingest_and_embed,
        "date",
        id="ingest_and_embed_startup",
    )

    logger.info(
        "Worker started — ingest every %d minutes for categories: %s",
        settings.arxiv_ingest_interval_minutes,
        settings.arxiv_categories,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker shutting down")
