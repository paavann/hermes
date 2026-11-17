import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from hermes_db import close_db, init_db
from hermes_worker.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_lifespan(*, sync_sources: bool = True) -> AsyncGenerator[None]:
    settings: Settings = get_settings()
    logger.info("initializing database connection for %s...", settings.APP)
    await init_db(db_url=settings.db_url, sync_sources=sync_sources)
    logger.info("database connection initialized.")
    try:
        yield
    finally:
        logger.info("closing database connections...")
        await close_db()
