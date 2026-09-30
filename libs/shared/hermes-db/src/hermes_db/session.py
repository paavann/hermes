import logging
from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from hermes_db.core.config import settings
from hermes_db.services import sync_sources_from_config


logger = logging.getLogger(__name__)


engine = create_async_engine(
    settings.db_url,
    echo=False,
    pool_size=5, pool_pre_ping=True,
    max_overflow=10,
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except:
            await session.rollback()
            raise


async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("successfully connected to the database.")
    except Exception:
        logger.error("failed to connect to the database.")
        raise

    try:
        async with AsyncSessionLocal() as session:
            await sync_sources_from_config(session=session)
    except Exception:
        logger.error("failed to sync sources from config.")


async def close_db() -> None:
    await engine.dispose()
    logger.info("database connection closed.")