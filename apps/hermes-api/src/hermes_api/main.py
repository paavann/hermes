"""Sample Hello World application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from hermes_api.db.db import engine

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Verify DB connection
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to the database!")
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")
        raise e
        
    yield
    
    # Shutdown: Clean up DB engine
    logger.info("Disposing database engine...")
    await engine.dispose()

app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "Hermes-API"}
