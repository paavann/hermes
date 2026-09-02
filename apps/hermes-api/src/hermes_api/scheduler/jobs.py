import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from hermes_api.core import settings
from hermes_api.services.ingestion_service import IngestionService
from hermes_api.services.event_service import EventService
from hermes_api.db.db import AsyncSessionLocal


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
    logger.info("settings up background jobs...")
    scheduler.add_job(
        run_ingestion_job,
        trigger=IntervalTrigger(minutes=settings.RSS_FETCH_INTERVAL_MINUTES),
        id="ingestion_job",
        replace_existing=True,
    )
    scheduler.add_job(
        run_lifecycle_job,
        trigger=IntervalTrigger(minutes=30),
        id="lifecycle_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler started.")



def shutdown_scheduler() -> None:
    logger.info("shutting down scheduler...")
    scheduler.shutdown(wait=False)
