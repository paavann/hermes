from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from hermes_api.core.config import settings
import hermes_api.db.models


engine = create_async_engine(
    settings.db_url, 
    echo=settings.is_dev,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session