import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hermes_db import close_db, init_db
from hermes_api.api.v1.router import api_router
from hermes_api.core.config import settings
from hermes_api.core.errors import register_err_handlers
from hermes_api.core.logger import setup_logging


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info(
        "initializing database connection to %s:%s/%s...",
        settings.DB_HOST,
        settings.DB_PORT,
        settings.DB_NAME,
    )
    await init_db(db_url=settings.db_url)

    logger.info("hermes api running on port %s.", settings.API_PORT)
    if not settings.LLM_API or not settings.LLM_MODEL:
        logger.warning(
            "llm credentials not configured. timeline synthesis will be unavailable."
        )
    yield

    logger.info("shutting down server...")
    await close_db()


app = FastAPI(title="hermes api", version=settings.VERSION, lifespan=lifespan)
register_err_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_BASE_PATH)


@app.get("/")
def index() -> dict[str, str]:
    return {"message": "hermes is running..."}
