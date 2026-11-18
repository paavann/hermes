import argparse
import enum
import logging
from hermes_db.session import AsyncSessionLocal
from hermes_worker.core.config import Settings, get_settings
from hermes_worker.jobs.commands import run_healthcheck, run_maintain_events
from hermes_worker.services.reset import (
    ResetGuardError,
    reset_local_schema,
    validate_reset_target,
)


logger = logging.getLogger(__name__)
settings: Settings = get_settings()


class WorkerCmd(enum.StrEnum):
    MAINTAIN_EVENTS = "maintain-events"
    HEALTHCHECK = "healthcheck"
    RESET = "reset-db"


async def handle_maintain_events(_args: argparse.Namespace) -> None:
    await run_maintain_events(settings=settings)


async def handle_healthcheck(_args: argparse.Namespace) -> None:
    await run_healthcheck(settings=settings)


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
