import logging

from hermes_db.services import EventService
from hermes_db.session import AsyncSessionLocal
from hermes_worker.core.config import Settings


logger = logging.getLogger(__name__)


async def run_lifecycle(settings: Settings) -> dict[str, int]:
    logger.info("starting event lifecycle transitions...")
    try:
        async with AsyncSessionLocal() as session:
            event_service = EventService(session)
            stats = await event_service.run_lifecycle_transitions(
                stale_hours=settings.EVENT_STALE_HOURS,
                archive_hours=settings.EVENT_ARCHIVE_HOURS,
            )
            logger.info("event lifecycle complete: %s.", stats)
            return stats
    except Exception:
        logger.exception("event lifecycle job failed.")
        raise
