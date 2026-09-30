import uuid
from datetime import UTC, datetime
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_db.enums import EventTlStatus
from hermes_db.models import Event, EventTl


class EventTlService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


    async def get_event(self, event_id: uuid.UUID) -> Event | None:
        return await self._session.get(Event, event_id)


    async def get_tl(self, event_id: uuid.UUID) -> EventTl | None:
        stmt = select(EventTl).where(EventTl.event_id == event_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


    async def create_tl(self, event_id: uuid.UUID, status: EventTlStatus) -> EventTl:
        existing_tl = EventTl(event_id=event_id, status=status)
        self._session.add(existing_tl)
        await self._session.commit()
        return existing_tl


    async def update_tl_status(self, tl: EventTl, status: EventTlStatus) -> None:
        tl.status = status
        await self._session.commit()


    async def save_generated_tl(
        self,
        tl: EventTl,
        nodes: list[dict], edges: list[dict],
        tl_summary: str,
        wikipedia_title: str, page_count: int,
        node_count: int,
        status: EventTlStatus,
    ) -> None:
        tl.nodes = nodes
        tl.edges = edges
        tl.tl_summary = tl_summary
        tl.wikipedia_title = wikipedia_title
        tl.page_count = page_count
        tl.node_count = node_count
        tl.status = status
        tl.generated_at = datetime.now(UTC)
        await self._session.commit()


    async def delete_tl(self, tl: EventTl) -> None:
        await self._session.delete(tl)
        await self._session.commit()


    async def get_event_coordinates(self, event_id: uuid.UUID) -> tuple[float | None, float | None]:
        stmt = select(
            ST_Y(Event.location).label("latitude"),
            ST_X(Event.location).label("longitude"),
        ).where(Event.id == event_id)
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row:
            return row.latitude, row.longitude
        return None, None
