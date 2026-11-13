import logging
from collections.abc import AsyncGenerator

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from hermes_db.services import sync_sources_from_config


logger = logging.getLogger(__name__)


engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise


async def init_db(db_url: URL | str | None = None) -> None:
    global engine

    if db_url is not None:
        if engine is not None:
            await engine.dispose()
        engine = create_async_engine(
            db_url,
            echo=False,
            pool_size=5,
            pool_pre_ping=True,
            max_overflow=10,
            connect_args={"statement_cache_size": 0},
        )
        AsyncSessionLocal.configure(bind=engine)
    elif engine is None:
        raise ValueError(
            "db_url must be provided when database engine is not initialized."
        )

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
        logger.exception("failed to sync sources from config.")


async def close_db() -> None:
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None
    logger.info("database connection closed.")
