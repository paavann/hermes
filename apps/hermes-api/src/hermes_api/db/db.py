from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from hermes_api.core.config import settings


engine = create_async_engine(
    settings.db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
