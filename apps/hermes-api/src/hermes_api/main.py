from fastapi import FastAPI
from sqlalchemy import text
from contextlib import asynccontextmanager
import logging

from hermes_api.db.db import engine
from hermes_api.core.logger import setup_logging
from hermes_api.api.v1.router import api_router
from hermes_api.scheduler.jobs import setup_scheduler, shutdown_scheduler


setup_logging()
logger = logging.getLogger(__name__)





@asynccontextmanager
async def lifespan(app: FastAPI):
    # server startup.
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("successfully connected to the database.")
    except Exception:
        logger.exception("failed to connect to the database.")
        raise

    setup_scheduler()

    # server runtime.
    yield

    # server shutdown.
    logger.info("shutting down server...")
    shutdown_scheduler()
    await engine.dispose()





app = FastAPI(
    title="hermes api",
    lifespan=lifespan,
    root_path="/api/v1"
)

app.include_router(api_router)

@app.get("/")
def index():
    return { "message": "hermes is running..." }
