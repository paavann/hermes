import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hermes_db import close_db, init_db
from utils_py import setup_logging
from hermes_api.api.v1.router import api_router
from hermes_api.core.config import settings
from hermes_api.core.errors import register_err_handlers
from hermes_api.services.ai_service import AiService
from hermes_api.services.chat_service import ChatRuntime


setup_logging()
logger = logging.getLogger(__name__)


def create_ai_services() -> tuple[AiService | None, ChatRuntime | None]:
    ai_service: AiService | None = None
    chat_runtime: ChatRuntime | None = None
    try:
        ai_service = AiService(settings)
        chat_runtime = (
            ChatRuntime.from_settings(settings, ai_service=ai_service)
            if ai_service is not None
            else None
        )
        if chat_runtime is None:
            logger.warning(
                "conversational chat is unavailable and will return 503 error."
            )
    except Exception as exc:
        logger.warning(
            "failed to configure ai service. ai features will be unavailable. error: %s.", exc
        )
    return ai_service, chat_runtime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info(
        "initializing database connection to %s:%s/%s...",
        settings.DB_HOST,
        settings.DB_PORT,
        settings.DB_NAME,
    )
    await init_db(db_url=settings.db_url)

    ai_service, chat_runtime = create_ai_services()
    app.state.ai_service = ai_service
    app.state.chat_runtime = chat_runtime

    logger.info("hermes api running on port %s.", settings.API_PORT)
    yield

    logger.info("shutting down server...")
    if chat_runtime is not None:
        await chat_runtime.aclose()
    if ai_service is not None:
        await ai_service.aclose()
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
