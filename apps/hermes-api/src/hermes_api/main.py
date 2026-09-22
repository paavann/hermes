import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from hermes_api.api.v1.router import api_router
from hermes_api.core.errors import register_err_handlers
from hermes_api.core.logger import setup_logging
from hermes_api.db.db import AsyncSessionLocal, engine
from hermes_api.scheduler.jobs import setup_scheduler
from hermes_api.scheduler.jobs import shutdown_scheduler
from hermes_api.services.source_service import sync_sources_from_config

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("successfully connected to the database.")
    except Exception:
        logger.exception("failed to connect to the database.")
        raise

    try:
        async with AsyncSessionLocal() as session:
            await sync_sources_from_config(session)
    except Exception:
        logger.exception("failed to sync sources from config.")

    setup_scheduler()

    logger.info("hermes API running on http://localhost:8000.")
    yield

    logger.info("shutting down server...")
    shutdown_scheduler()
    await engine.dispose()


app = FastAPI(title="hermes api", lifespan=lifespan, root_path="/api/v1")
register_err_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def index() -> dict[str, str]:
    return {"message": "hermes is running..."}
