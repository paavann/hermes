import argparse
import enum
import logging
from hermes_worker.services.lifecycle import run_lifecycle
from hermes_worker.services.sync import SyncService


logger = logging.getLogger("hermes_worker")


class WorkerCmd(enum.StrEnum):
    SYNC = "run-sync"
    LIFECYCLE = "run-lifecycle"
    ALL = "run-all"


async def handle_sync(args: argparse.Namespace) -> None:
    service = SyncService()
    stats = await service.sync_all_sources(force=args.force)
    logger.info("sync finished: %s.", stats)


async def handle_lifecycle(_args: argparse.Namespace) -> None:
    stats = await run_lifecycle()
    logger.info("lifecycle transitions finished: %s.", stats)


async def handle_all(args: argparse.Namespace) -> None:
    lifecycle_stats = await run_lifecycle()
    logger.info("lifecycle transitions finished: %s.", lifecycle_stats)
    service = SyncService()
    sync_stats = await service.sync_all_sources(force=args.force)
    logger.info("sync finished: %s.", sync_stats)
