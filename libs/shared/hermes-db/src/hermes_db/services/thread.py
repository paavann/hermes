import uuid
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import ThreadKind
from hermes_db.models.event import Event
from hermes_db.models.thread import Thread
from hermes_db.utils.datetime import ensure_utc


class ThreadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_thread(
        self,
        name: str,
        *,
        kind: ThreadKind = ThreadKind.DEVELOPING,
        description: str | None = None,
        entities: list[dict[str, object]] | None = None,
        keywords: list[str] | None = None,
        started_at: datetime | None = None,
    ) -> Thread:
        thread = Thread(
            name=name,
            kind=kind,
            description=description,
            entities=entities or [],
            keywords=keywords or [],
            started_at=ensure_utc(started_at) if started_at is not None else None,
        )
        self._session.add(thread)
        await self._session.flush()
        return thread

    async def get_thread(self, thread_id: uuid.UUID) -> Thread | None:
        return await self._session.get(Thread, thread_id)

    async def assign_event(self, event_id: uuid.UUID, thread_id: uuid.UUID) -> bool:
        stmt = update(Event).where(Event.id == event_id).values(thread_id=thread_id)
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount > 0
        return False
