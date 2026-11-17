import argparse
import enum
import logging
from hermes_db.session import AsyncSessionLocal
from hermes_worker.core.config import Settings, get_settings
from hermes_worker.services.lifecycle import run_lifecycle
from hermes_worker.services.reset import (
    ResetGuardError,
    reset_local_schema,
    validate_reset_target,
)
from hermes_worker.services.sync import SyncService


logger = logging.getLogger(__name__)
settings: Settings = get_settings()


class WorkerCmd(enum.StrEnum):
    SYNC = "run-sync"
    LIFECYCLE = "run-lifecycle"
    ALL = "run-all"
    RESET = "reset-db"


async def handle_sync(args: argparse.Namespace) -> None:
    service = SyncService(settings=settings)
    stats = await service.sync_all_sources(force=args.force)
    logger.info("sync finished: %s.", stats)


async def handle_lifecycle(_args: argparse.Namespace) -> None:
    stats = await run_lifecycle(settings)
    logger.info("lifecycle transitions finished: %s.", stats)


async def handle_all(args: argparse.Namespace) -> None:
    lifecycle_stats = await run_lifecycle(settings)
    logger.info("lifecycle transitions finished: %s.", lifecycle_stats)
    service = SyncService(settings=settings)
    sync_stats = await service.sync_all_sources(force=args.force)
    logger.info("sync finished: %s.", sync_stats)


async def handle_reset_db(args: argparse.Namespace) -> None:
    if not getattr(args, "yes", False):
        raise ResetGuardError(
            "refusing to reset the database without explicit confirmation; "
            "re-run with --yes."
        )
    validate_reset_target(
        env=settings.ENV,
        db_host=settings.DB_HOST,
        db_name=settings.DB_NAME,
    )
    logger.warning(
        "resetting local database '%s' at %s:%s.",
        settings.DB_NAME,
        settings.DB_HOST,
        settings.DB_PORT,
    )
    async with AsyncSessionLocal() as session:
        await reset_local_schema(session)
    logger.info(
        "database reset complete. run 'npx nx run hermes-db:migrate' "
        "to rebuild the schema, then restart any running API/worker processes."
    )
