import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from hermes_db import close_db, init_db
from hermes_worker.core.config import settings


logger = logging.getLogger("hermes_worker")


@asynccontextmanager
async def db_lifespan() -> AsyncGenerator[None]:
    logger.info("initializing database connection for %s...", settings.APP)
    await init_db(db_url=settings.db_url)
    logger.info("database connection initialized.")
    try:
        yield
    finally:
        logger.info("closing database connections...")
        await close_db()
