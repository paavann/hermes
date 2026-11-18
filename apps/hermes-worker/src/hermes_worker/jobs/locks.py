from __future__ import annotations
import enum
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Final
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine


logger = logging.getLogger(__name__)


class LockName(enum.StrEnum):
    INGEST_ARTICLES = "ingest-articles"
    MAINTAIN_EVENTS = "maintain-events"
    HEALTHCHECK = "healthcheck"


# stable 64-bit keys. each command has its own lock so a short maintenance run
# cannot block a diagnostic probe, while repeated runs of one command still skip.
LOCK_KEYS: Final[dict[LockName, int]] = {
    LockName.INGEST_ARTICLES: 824_100_005,
    LockName.MAINTAIN_EVENTS: 824_100_003,
    LockName.HEALTHCHECK: 824_100_004,
}


def lock_key(name: LockName) -> int:
    try:
        return LOCK_KEYS[name]
    except KeyError as exc:
        raise ValueError(f"unknown job lock '{name}'.") from exc


@asynccontextmanager
async def advisory_lock(engine: AsyncEngine, key: int) -> AsyncGenerator[bool]:
    """Try to take a session-level Postgres advisory lock."""
    async with engine.connect() as conn:
        acquired = bool(await conn.scalar(select(func.pg_try_advisory_lock(key))))
        if not acquired:
            logger.warning("job advisory lock %s is already held.", key)
        try:
            yield acquired
        finally:
            if acquired:
                await conn.execute(select(func.pg_advisory_unlock(key)))
