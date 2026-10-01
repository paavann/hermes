import argparse
import asyncio
import logging
import sys
from hermes_db import close_db, init_db
from hermes_worker.core.config import settings
from hermes_worker.core.logger import setup_logging
from hermes_worker.services.ingestion import IngestionService
from hermes_worker.services.lifecycle import run_lifecycle


logger = logging.getLogger("hermes_worker")


async def _run_command(command: str, force: bool = False) -> int:
    logger.info("initializing database connection for %s...", settings.APP)
    await init_db(db_url=str(settings.db_url))
    try:
        if command == "run-ingestion":
            service = IngestionService()
            stats = await service.ingest_all_sources(force=force)
            logger.info("ingestion finished: %s", stats)
        elif command == "run-lifecycle":
            stats = await run_lifecycle()
            logger.info("lifecycle transitions finished: %s", stats)
        elif command == "run-all":
            lifecycle_stats = await run_lifecycle()
            logger.info("lifecycle transitions finished: %s", lifecycle_stats)
            service = IngestionService()
            ingest_stats = await service.ingest_all_sources(force=force)
            logger.info("ingestion finished: %s", ingest_stats)
        else:
            logger.error("unknown command: %s", command)
            return 1
        return 0
    except Exception:
        logger.exception("worker execution failed for command '%s'.", command)
        return 1
    finally:
        logger.info("closing database connections...")
        await close_db()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-worker",
        description="Hermes Ephemeral Data Ingestion & Event Lifecycle Worker",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-ingestion.
    ingest_p = subparsers.add_parser(
        "run-ingestion", help="Execute RSS source ingestion cycle"
    )
    ingest_p.add_argument(
        "--force",
        action="store_true",
        help="Force ingestion of all sources regardless of interval",
    )

    # run-lifecycle.
    subparsers.add_parser(
        "run-lifecycle",
        help="Execute event score decay and status transitions",
    )

    # run-all.
    all_p = subparsers.add_parser(
        "run-all",
        help="Execute lifecycle transitions followed by due ingestion",
    )
    all_p.add_argument(
        "--force",
        action="store_true",
        help="Force ingestion of all sources regardless of interval",
    )

    return parser


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()
    force = getattr(args, "force", False)
    exit_code = asyncio.run(_run_command(command=args.command, force=force))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
