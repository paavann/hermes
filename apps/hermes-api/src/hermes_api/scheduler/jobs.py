import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from hermes_api.core.config import settings
from hermes_api.db.db import AsyncSessionLocal
from hermes_api.services.event_service import EventService
from hermes_api.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_ingestion_job(force: bool = False, is_startup: bool = False) -> None:
    job_name = "startup ingestion cycle" if is_startup else "ingestion job"
    logger.info("starting %s...", job_name)
    try:
        service = IngestionService()
        stats = await service.ingest_all_sources(force=force)
        logger.info("%s complete: %s.", job_name, stats)
    except Exception:
        logger.exception("%s failed.", job_name)


async def run_event_lifecycle_job() -> None:
    logger.info("starting event lifecycle job...")
    try:
        async with AsyncSessionLocal() as session:
            event_service = EventService(session)
            stats = await event_service.run_lifecycle_transitions()
            logger.info("event lifecycle complete: %s.", stats)
    except Exception:
        logger.exception("event lifecycle job failed.")





_startup_task = None

def setup_scheduler() -> None:
    logger.info("setting up background jobs...")

    scheduler.add_job(
        run_ingestion_job,
        trigger=IntervalTrigger(minutes=settings.INGESTION_HEARTBEAT_MIN),
        id="ingestion_job",
        replace_existing=True,
    )

    scheduler.add_job(
        run_event_lifecycle_job,
        trigger=IntervalTrigger(minutes=60),
        id="event_lifecycle_job",
        replace_existing=True,
    )



    scheduler.start()
    logger.info(
        "scheduler started. ingestion will run every %s minutes.",
        settings.INGESTION_HEARTBEAT_MIN,
    )

    # this is to ensure the ingestion runs on app startup regardless of the cron job interval.
    global _startup_task
    _startup_task = asyncio.create_task(run_ingestion_job(force=True, is_startup=True))


def shutdown_scheduler() -> None:
    logger.info("shutting down scheduler...")
    scheduler.shutdown(wait=False)
