import asyncio
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from hermes_api.core.config import settings
from hermes_api.main import lifespan


def test_lifespan_initializes_and_closes_db():
    async def _test():
        app = FastAPI()
        with (
            patch("hermes_api.main.init_db", new_callable=AsyncMock) as mock_init_db,
            patch("hermes_api.main.close_db", new_callable=AsyncMock) as mock_close_db,
        ):
            async with lifespan(app):
                mock_init_db.assert_awaited_once_with(db_url=settings.db_url)
                mock_close_db.assert_not_awaited()

            mock_close_db.assert_awaited_once()

    asyncio.run(_test())
