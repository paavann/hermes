import logging
from hermes_db.services import EventService
from hermes_db.session import AsyncSessionLocal


logger = logging.getLogger(__name__)


async def run_lifecycle() -> dict[str, int]:
    logger.info("starting event lifecycle transitions...")
    try:
        async with AsyncSessionLocal() as session:
            event_service = EventService(session)
            stats = await event_service.run_lifecycle_transitions()
            logger.info("event lifecycle complete: %s.", stats)
            return stats
    except Exception:
        logger.exception("event lifecycle job failed.")
        raise
