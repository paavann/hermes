"""Shared pytest fixtures and helpers for hermes_db unit tests.

All tests in this suite are **pure unit tests** — they never touch a real
database.  Every SQLAlchemy AsyncSession is replaced by a carefully
constructed MagicMock / AsyncMock so that:

* The test suite can run without any running PostgreSQL instance.
* Individual service methods can be verified in perfect isolation.
* Side-effects (session.add, session.commit, …) are recorded and asserted.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from hermes_db.enums import EventStatus
from hermes_db.models import Article, Event, Source


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def make_uuid() -> uuid.UUID:
    """Return a fresh random UUID."""
    return uuid.uuid4()


def utcnow() -> datetime:
    """Return the current UTC time (tz-naive, matching the production code)."""
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Model factory helpers
# ---------------------------------------------------------------------------


def make_event(
    *,
    id: uuid.UUID | None = None,
    status: EventStatus = EventStatus.ACTIVE,
    trending_score: float = 5.0,
    article_count: int = 1,
    ai_headline: str = "Test headline",
    category: str = "Politics",
    location_name: str | None = "London, UK",
    last_updated_at: datetime | None = None,
    embedding: list[float] | None = None,
) -> MagicMock:
    """Build a mock Event ORM object with sensible defaults."""
    evt = MagicMock(spec=Event)
    evt.id = id or make_uuid()
    evt.status = status
    evt.trending_score = trending_score
    evt.article_count = article_count
    evt.ai_headline = ai_headline
    evt.category = category
    evt.location_name = location_name
    evt.last_updated_at = last_updated_at or utcnow()
    evt.embedding = embedding
    return evt


def make_source(
    *,
    slug: str = "test-source",
    name: str = "Test Source",
    url: str = "https://example.com",
    feed_url: str | None = "https://example.com/rss",
    credibility: str = "TIER_3",
    is_active: bool = True,
) -> MagicMock:
    """Build a mock Source ORM object with sensible defaults."""
    src = MagicMock(spec=Source)
    src.slug = slug
    src.name = name
    src.url = url
    src.feed_url = feed_url
    src.credibility = credibility
    src.is_active = is_active
    return src


def make_article(
    *,
    id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
    source_id: uuid.UUID | None = None,
    title: str = "Test article",
    url: str = "https://example.com/article",
) -> MagicMock:
    """Build a mock Article ORM object with sensible defaults."""
    art = MagicMock(spec=Article)
    art.id = id or make_uuid()
    art.event_id = event_id or make_uuid()
    art.source_id = source_id or make_uuid()
    art.title = title
    art.url = url
    return art


# ---------------------------------------------------------------------------
# Session mock factory
# ---------------------------------------------------------------------------


def make_async_session(
    *,
    get_return: Any = None,
    execute_scalars: list[Any] | None = None,
    execute_scalar_one_or_none: Any = None,
    execute_all: list[Any] | None = None,
    execute_rowcount: int = 0,
) -> AsyncMock:
    """Build a flexible AsyncSession mock.

    Parameters
    ----------
    get_return:
        Value returned by ``session.get(Model, pk)``.
    execute_scalars:
        If set, ``result.scalars().all()`` returns this list.
    execute_scalar_one_or_none:
        If set, ``result.scalar_one_or_none()`` returns this value.
    execute_all:
        If set, ``result.all()`` returns this iterable.
    execute_rowcount:
        Value of ``result.rowcount`` (for UPDATE statements).
    """
    session = AsyncMock()
    session.get = AsyncMock(return_value=get_return)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()

    result = MagicMock()
    result.rowcount = execute_rowcount
    result.scalar_one_or_none = MagicMock(return_value=execute_scalar_one_or_none)

    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=execute_scalars or [])
    result.scalars = MagicMock(return_value=scalars_mock)

    result.all = MagicMock(return_value=execute_all or [])

    session.execute = AsyncMock(return_value=result)
    return session


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------


def run(coro):
    """Run a coroutine synchronously (thin wrapper around asyncio.run)."""
    return asyncio.run(coro)
