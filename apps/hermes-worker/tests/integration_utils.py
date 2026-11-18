"""Shared helpers for tests that need a disposable migrated database."""

import os
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool


def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping database integration test.")
    return url


def make_engine() -> AsyncEngine:
    return create_async_engine(
        database_url(),
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )


async def require_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        exists = bool(
            await conn.scalar(
                text(
                    "SELECT to_regclass('public.articles') IS NOT NULL "
                    "AND EXISTS ("
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'articles' "
                    "AND column_name = 'attempt_count'"
                    ")"
                )
            )
        )
    if not exists:
        pytest.skip(
            "integration database is not migrated; run alembic upgrade head first."
        )
