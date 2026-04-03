"""Standalone task runners for manual invocation via CLI."""

import asyncio
import logging
import argparse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


async def run_ingest(max_results: int):
    from app.services.arxiv_ingest import ingest_papers

    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        count = await ingest_papers(db, max_results=max_results)
        print(f"Ingested {count} papers")
    await engine.dispose()


async def run_embed(batch_size: int):
    from app.services.embeddings import compute_embeddings

    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        count = await compute_embeddings(db, batch_size=batch_size)
        print(f"Embedded {count} papers")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run worker tasks manually")
    sub = parser.add_subparsers(dest="task")

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("-n", "--max-results", type=int, default=500)

    p_embed = sub.add_parser("embed")
    p_embed.add_argument("-b", "--batch-size", type=int, default=128)

    args = parser.parse_args()

    if args.task == "ingest":
        asyncio.run(run_ingest(args.max_results))
    elif args.task == "embed":
        asyncio.run(run_embed(args.batch_size))
    else:
        parser.print_help()
