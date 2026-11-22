from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import EventStatus
from hermes_db.models.event import Event


DEFAULT_STALE_HOURS = 72
DEFAULT_ARCHIVE_HOURS = 168


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    staled: int
    archived: int


class EventLifecycleService:
    """Applies the boring, deterministic event retention state machine."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run(
        self,
        *,
        now: datetime | None = None,
        stale_hours: int = DEFAULT_STALE_HOURS,
        archive_hours: int = DEFAULT_ARCHIVE_HOURS,
    ) -> LifecycleResult:
        moment = now or datetime.now(UTC)
        stale_cutoff = moment - timedelta(hours=stale_hours)
        archive_cutoff = moment - timedelta(hours=archive_hours)

        anchor = Event.latest_published_at
        staled = await self._session.execute(
            update(Event)
            .where(Event.status == EventStatus.ACTIVE)
            .where(Event.merged_into_id.is_(None))
            .where(anchor.is_not(None))
            .where(anchor < stale_cutoff)
            .values(status=EventStatus.STALE)
            .execution_options(synchronize_session=False)
        )
        archived = await self._session.execute(
            update(Event)
            .where(Event.status == EventStatus.STALE)
            .where(Event.merged_into_id.is_(None))
            .where(anchor.is_not(None))
            .where(anchor < archive_cutoff)
            .values(status=EventStatus.ARCHIVED)
            .execution_options(synchronize_session=False)
        )
        return LifecycleResult(
            staled=_rowcount(staled),
            archived=_rowcount(archived),
        )

    async def reactivate_stale(self, event_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            update(Event)
            .where(Event.id == event_id)
            .where(Event.status == EventStatus.STALE)
            .values(status=EventStatus.ACTIVE)
            .execution_options(synchronize_session=False)
        )
        return _rowcount(result) > 0

    async def purge_archived_embeddings(
        self,
        *,
        now: datetime | None = None,
        after_days: int = 30,
    ) -> int:
        moment = now or datetime.now(UTC)
        cutoff = moment - timedelta(days=after_days)
        result = await self._session.execute(
            update(Event)
            .where(Event.status == EventStatus.ARCHIVED)
            .where(Event.embedding.is_not(None))
            .where(
                or_(
                    Event.latest_published_at.is_(None),
                    Event.latest_published_at < cutoff,
                )
            )
            .values(embedding=None, embedding_model=None)
            .execution_options(synchronize_session=False)
        )
        return _rowcount(result)


def _rowcount(result: object) -> int:
    if isinstance(result, CursorResult):
        return int(result.rowcount or 0)
    return 0
