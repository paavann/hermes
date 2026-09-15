import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from hermes_api.core.config import settings
from hermes_api.db.db import AsyncSessionLocal
from hermes_api.services.event_service import EventService
from hermes_api.services.ingestion_service import IngestionService


logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_ingestion_job() -> None:
    logger.info("starting ingestion job...")
    try:
        service = IngestionService()
        stats = await service.ingest_all_sources()
        logger.info(f"ingestion complete: {stats}.")
    except Exception:
        logger.exception("ingestion job failed.")


async def run_event_lifecycle_job() -> None:
    logger.info("starting event lifecycle job...")
    try:
        async with AsyncSessionLocal() as session:
            event_service = EventService(session)
            stats = await event_service.run_lifecycle_transitions()
            logger.info(f"event lifecycle complete: {stats}.")
    except Exception:
        logger.exception("event lifecycle job failed.")


async def run_lineage_sync_job() -> None:
    logger.info("starting lineage sync job...")
    try:
        from hermes_api.services.lineage_service import LineageService

        async with AsyncSessionLocal() as session:
            lineage_service = LineageService(session)
            stats = await lineage_service.sync_allowlisted_stories()
            logger.info(f"scheduled lineage sync complete: {stats}")
    except Exception:
        logger.exception("scheduled lineage sync job failed.")


def setup_scheduler() -> None:
    logger.info("setting up background jobs...")

    scheduler.add_job(
        run_ingestion_job,
        trigger=IntervalTrigger(minutes=settings.INGESTION_HEARTBEAT_MINUTES),
        id="ingestion_job",
        replace_existing=True,
    )

    scheduler.add_job(
        run_event_lifecycle_job,
        trigger=IntervalTrigger(minutes=60),
        id="event_lifecycle_job",
        replace_existing=True,
    )

    scheduler.add_job(
        run_lineage_sync_job,
        trigger=IntervalTrigger(minutes=60),
        id="lineage_sync_job",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"scheduler started. the ingestion will now run at every {settings.INGESTION_HEARTBEAT_MINUTES} minutes."
    )

    # this is to ensure the ingestion runs on app startup regardless of the cron job interval.
    asyncio.ensure_future(_run_startup_ingestion())


async def _run_startup_ingestion() -> None:
    logger.info("running startup ingestion cycle...")
    await run_ingestion_job()
    logger.info("startup ingestion cycle complete.")


def shutdown_scheduler() -> None:
    logger.info("shutting down scheduler...")
    scheduler.shutdown(wait=False)
