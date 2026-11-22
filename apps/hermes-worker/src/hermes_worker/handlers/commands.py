import argparse
import enum
import logging
from hermes_db.services import load_sources_config
from hermes_db.session import AsyncSessionLocal
from hermes_worker.core.config import Settings, get_settings
from hermes_worker.jobs.commands import (
    run_build_events,
    run_healthcheck,
    run_ingest_articles,
    run_maintain_events,
)
from hermes_worker.services.reset import (
    ResetGuardError,
    reset_local_schema,
    validate_reset_target,
)
from hermes_worker.services.source_audit import audit_sources, format_audit


logger = logging.getLogger(__name__)
settings: Settings = get_settings()


class WorkerCmd(enum.StrEnum):
    INGEST_ARTICLES = "ingest-articles"
    BUILD_EVENTS = "build-events"
    MAINTAIN_EVENTS = "maintain-events"
    AUDIT_SOURCES = "audit-sources"
    HEALTHCHECK = "healthcheck"
    RESET = "reset-db"


async def handle_ingest_articles(args: argparse.Namespace) -> None:
    await run_ingest_articles(
        settings=settings,
        force=bool(getattr(args, "force", False)),
    )


async def handle_build_events(_args: argparse.Namespace) -> None:
    await run_build_events(settings=settings)


async def handle_maintain_events(args: argparse.Namespace) -> None:
    requeue_since = getattr(args, "since", None)
    if getattr(args, "requeue", False) and requeue_since is None:
        raise ValueError("--requeue requires --since <YYYY-MM-DD>.")
    await run_maintain_events(
        settings=settings,
        requeue_since=requeue_since,
    )


async def handle_healthcheck(_args: argparse.Namespace) -> None:
    await run_healthcheck(settings=settings)


async def handle_audit_sources(_args: argparse.Namespace) -> None:
    entries = await load_sources_config()
    audits = await audit_sources(
        entries,
        user_agent=settings.NOMINATIM_USER_AGENT,
        concurrency=settings.SOURCE_FETCH_CONCURRENCY,
    )
    for line in format_audit(audits):
        logger.info("%s", line)


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
