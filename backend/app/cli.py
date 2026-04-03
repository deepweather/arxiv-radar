"""CLI commands for arxiv-radar backend.

Usage:
    python -m app.cli backfill status
    python -m app.cli backfill start --batch-size=100
    python -m app.cli backfill run-once --batch-size=50
    python -m app.cli backfill reset
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


def get_session_factory():
    engine = create_async_engine(settings.database_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def cmd_backfill_status():
    """Show backfill status."""
    from app.services.backfill import get_backfill_status
    
    factory = get_session_factory()
    async with factory() as db:
        status = await get_backfill_status(db)
    
    print("\n=== Backfill Status ===")
    print(f"Status:           {status['status']}")
    print(f"Total papers:     {status['total_papers']:,}")
    print(f"Papers processed: {status['papers_processed']:,}")
    print(f"Cursor offset:    {status.get('cursor_offset', 0):,}")
    print(f"Last paper date:  {status.get('last_paper_date') or 'N/A'}")
    print(f"Is complete:      {status['is_complete']}")
    print(f"Started at:       {status['started_at'] or 'N/A'}")
    print(f"Last run at:      {status['last_run_at'] or 'N/A'}")
    print()


async def cmd_backfill_run_once(batch_size: int, dry_run: bool = False):
    """Run a single backfill batch."""
    from app.services.backfill import run_backfill_batch
    
    factory = get_session_factory()
    async with factory() as db:
        result = await run_backfill_batch(db, batch_size=batch_size, dry_run=dry_run)
    
    print("\n=== Backfill Batch Result ===")
    print(f"Status:         {result['status']}")
    print(f"Papers fetched: {result['papers_fetched']}")
    print(f"New papers:     {result['new_papers']}")
    print(f"Cursor offset:  {result.get('cursor_offset', 0)}")
    print(f"Last paper:     {result.get('last_paper_date') or 'N/A'}")
    print(f"Is complete:    {result['is_complete']}")
    if dry_run:
        print("(DRY RUN - no changes made)")
    print()


async def cmd_backfill_start(batch_size: int, max_batches: int = 0, delay_between: int = 60):
    """Run backfill continuously until complete."""
    from app.services.backfill import run_backfill_batch, get_backfill_status
    
    factory = get_session_factory()
    batches_run = 0
    
    print(f"\n=== Starting Continuous Backfill ===")
    print(f"Batch size: {batch_size}")
    print(f"Max batches: {max_batches or 'unlimited'}")
    print(f"Delay between batches: {delay_between}s")
    print()
    
    while True:
        async with factory() as db:
            result = await run_backfill_batch(db, batch_size=batch_size)
        
        batches_run += 1
        print(f"[Batch {batches_run}] Fetched {result['papers_fetched']} papers, "
              f"{result['new_papers']} new, offset: {result.get('cursor_offset', 0)}, "
              f"latest: {result.get('last_paper_date', 'N/A')}")
        
        if result['is_complete']:
            print("\n=== Backfill Complete! ===")
            break
        
        if max_batches > 0 and batches_run >= max_batches:
            print(f"\n=== Reached max batches ({max_batches}), stopping ===")
            break
        
        print(f"Waiting {delay_between}s before next batch...")
        await asyncio.sleep(delay_between)
    
    async with factory() as db:
        status = await get_backfill_status(db)
    print(f"Total papers in database: {status['total_papers']:,}")


async def cmd_backfill_reset():
    """Reset backfill state to start over."""
    from app.services.backfill import reset_backfill
    
    confirm = input("Are you sure you want to reset backfill state? [y/N] ")
    if confirm.lower() != 'y':
        print("Aborted")
        return
    
    factory = get_session_factory()
    async with factory() as db:
        await reset_backfill(db)
    
    print("Backfill state reset successfully")


async def cmd_embed_pending():
    """Generate embeddings for papers without them."""
    from app.services.embeddings import compute_embeddings
    
    factory = get_session_factory()
    async with factory() as db:
        count = await compute_embeddings(db)
    
    print(f"Embedded {count} papers")


def main():
    parser = argparse.ArgumentParser(description="arxiv-radar CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Backfill commands
    backfill_parser = subparsers.add_parser("backfill", help="Manage historical paper backfill")
    backfill_sub = backfill_parser.add_subparsers(dest="subcommand", required=True)
    
    # backfill status
    backfill_sub.add_parser("status", help="Show backfill status")
    
    # backfill run-once
    run_once = backfill_sub.add_parser("run-once", help="Run a single backfill batch")
    run_once.add_argument("--batch-size", type=int, default=100, help="Papers per batch")
    run_once.add_argument("--dry-run", action="store_true", help="Don't actually insert papers")
    
    # backfill start
    start = backfill_sub.add_parser("start", help="Run backfill continuously")
    start.add_argument("--batch-size", type=int, default=100, help="Papers per batch")
    start.add_argument("--max-batches", type=int, default=0, help="Max batches (0=unlimited)")
    start.add_argument("--delay", type=int, default=60, help="Seconds between batches")
    
    # backfill reset
    backfill_sub.add_parser("reset", help="Reset backfill state")
    
    # Embed command
    subparsers.add_parser("embed", help="Generate embeddings for pending papers")
    
    args = parser.parse_args()
    
    if args.command == "backfill":
        if args.subcommand == "status":
            asyncio.run(cmd_backfill_status())
        elif args.subcommand == "run-once":
            asyncio.run(cmd_backfill_run_once(args.batch_size, args.dry_run))
        elif args.subcommand == "start":
            asyncio.run(cmd_backfill_start(args.batch_size, args.max_batches, args.delay))
        elif args.subcommand == "reset":
            asyncio.run(cmd_backfill_reset())
    elif args.command == "embed":
        asyncio.run(cmd_embed_pending())


if __name__ == "__main__":
    main()
