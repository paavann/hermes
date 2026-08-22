from fastapi import FastAPI
from sqlalchemy import text
from contextlib import asynccontextmanager
import logging
from hermes_api.db.db import engine
from hermes_api.core.logger import setup_logging


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

    # server runtime.
    yield

    # server shutdown.
    logger.info("disposing database engine...")
    await engine.dispose()





app = FastAPI(
    lifespan=lifespan,
    root_path="/api/v1"
)

@app.get("/")
def index():
    return { "message": "hermes is running..." }
