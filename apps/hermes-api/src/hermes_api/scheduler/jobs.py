import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from hermes_api.core.config import settings
from hermes_api.db.db import AsyncSessionLocal
from hermes_api.services.event_service import EventService
from hermes_api.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()





async def run_ingestion_job() -> None:
    logger.info("starting scheduled ingestion job...")
    try:
        service = IngestionService()
        stats = await service.ingest_all_sources()
        logger.info(f"scheduled ingestion complete: {stats}.")
    except Exception:
        logger.exception("scheduled ingestion job failed.")



async def run_lifecycle_job() -> None:
    logger.info("starting scheduled lifecycle job...")
    try:
        async with AsyncSessionLocal() as session:
            event_service = EventService(session)
            stats = await event_service.run_lifecycle_transitions()
            logger.info(f"scheduled lifecycle complete: {stats}")
    except Exception:
        logger.exception("scheduled lifecycle job failed.")


    
def setup_scheduler() -> None:
    logger.info("setting up background jobs...")

    # Ingestion: runs at configured cron hours (default: 6, 14, 22 UTC).
    scheduler.add_job(
        run_ingestion_job,
        trigger=CronTrigger(hour=settings.INGESTION_CRON_HOURS),
        id="ingestion_job",
        replace_existing=True,
    )

    # Lifecycle transitions: runs every 30 minutes.
    scheduler.add_job(
        run_lifecycle_job,
        trigger=IntervalTrigger(minutes=30),
        id="lifecycle_job",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"scheduler started. ingestion cron hours: "
        f"{settings.INGESTION_CRON_HOURS} UTC."
    )

    # Fire one immediate ingestion run on startup so the map
    # is populated right away, regardless of when the next cron fires.
    asyncio.ensure_future(_run_startup_ingestion())


async def _run_startup_ingestion() -> None:
    """Run a single ingestion cycle on startup.

    Wrapped in its own function so it runs as a background task
    without blocking the server from accepting requests.
    """
    logger.info("running startup ingestion cycle...")
    await run_ingestion_job()
    logger.info("startup ingestion cycle complete.")



def shutdown_scheduler() -> None:
    logger.info("shutting down scheduler...")
    scheduler.shutdown(wait=False)
