"""Background worker — single async event loop running all periodic tasks sequentially."""

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_engine = None
_session_factory = None
_job_lock: asyncio.Lock | None = None

# Backfill config from env
BACKFILL_ENABLED = os.getenv("BACKFILL_ENABLED", "false").lower() == "true"
BACKFILL_BATCH_SIZE = int(os.getenv("BACKFILL_BATCH_SIZE", "100"))
BACKFILL_INTERVAL_MINUTES = int(os.getenv("BACKFILL_INTERVAL_MINUTES", "30"))

# Digest email config from env
DIGEST_ENABLED = os.getenv("DIGEST_ENABLED", "false").lower() == "true"
DIGEST_HOUR_UTC = int(os.getenv("DIGEST_HOUR_UTC", "8"))


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
    from app.services.embeddings import compute_embeddings, ensure_hnsw_index

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

        async with factory() as db:
            try:
                await ensure_hnsw_index(db)
            except Exception:
                logger.exception("HNSW index creation failed")


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


async def run_backfill():
    """Run one batch of historical paper backfill."""
    from app.services.backfill import run_backfill_batch, get_backfill_status

    async with _get_job_lock():
        factory = _get_session_factory()

        async with factory() as db:
            try:
                status = await get_backfill_status(db)
                if status.get("is_complete"):
                    logger.info("Backfill already complete, skipping")
                    return
                
                result = await run_backfill_batch(db, batch_size=BACKFILL_BATCH_SIZE)
                logger.info(
                    "Backfill batch: fetched %d papers, %d new, latest: %s",
                    result["papers_fetched"],
                    result["new_papers"],
                    result.get("last_paper_date", "N/A"),
                )
                
                if result["is_complete"]:
                    logger.info("Backfill complete!")
            except Exception:
                logger.exception("Backfill failed")


async def run_email_digests():
    """Send email digests to users who have opted in."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.db.models import User
    from app.services.recommender import recommend_for_user
    from app.services.email import send_digest_email
    
    async with _get_job_lock():
        factory = _get_session_factory()
        
        async with factory() as db:
            try:
                today = datetime.now(timezone.utc)
                is_sunday = today.weekday() == 6
                
                result = await db.execute(
                    select(User).where(
                        User.digest_enabled == True,
                        User.is_email_verified == True,
                    )
                )
                users = result.scalars().all()
                
                sent_count = 0
                for user in users:
                    if user.digest_frequency == "weekly" and not is_sunday:
                        continue
                    
                    try:
                        papers = await recommend_for_user(db, str(user.id), limit=20, days=7)
                        if papers:
                            if send_digest_email(user.email, papers):
                                sent_count += 1
                    except Exception:
                        logger.exception("Failed to send digest to %s", user.email)
                
                logger.info("Email digests sent: %d", sent_count)
            except Exception:
                logger.exception("Email digest job failed")


async def run_startup():
    """Run all startup tasks sequentially to avoid connection pool conflicts."""
    logger.info("Running startup tasks...")
    await run_ingest_and_embed()
    # Citation fetching disabled - using external links instead
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

    # Citation fetching disabled - using external links instead (Semantic Scholar, Google Scholar)
    # scheduler.add_job(
    #     run_citation_fetch,
    #     "interval",
    #     minutes=10,
    #     id="citation_fetch",
    #     max_instances=1,
    #     coalesce=True,
    # )

    # Optional backfill job - only if enabled via env
    if BACKFILL_ENABLED:
        scheduler.add_job(
            run_backfill,
            "interval",
            minutes=BACKFILL_INTERVAL_MINUTES,
            id="backfill",
            max_instances=1,
            coalesce=True,
        )
        logger.info(
            "Backfill ENABLED — batch_size=%d, interval=%d minutes",
            BACKFILL_BATCH_SIZE,
            BACKFILL_INTERVAL_MINUTES,
        )
    else:
        logger.info("Backfill disabled (set BACKFILL_ENABLED=true to enable)")
    
    # Email digest job - daily at configured hour UTC
    if DIGEST_ENABLED:
        scheduler.add_job(
            run_email_digests,
            "cron",
            hour=DIGEST_HOUR_UTC,
            minute=0,
            id="email_digests",
            max_instances=1,
            coalesce=True,
        )
        logger.info("Email digests ENABLED — daily at %d:00 UTC", DIGEST_HOUR_UTC)
    else:
        logger.info("Email digests disabled (set DIGEST_ENABLED=true to enable)")

    scheduler.add_job(
        run_startup,
        "date",
        id="startup",
    )

    logger.info(
        "Worker started — ingest every %d minutes, categories: %s",
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
