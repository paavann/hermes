from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from geoalchemy2.functions import ST_X, ST_Y, ST_MakeEnvelope, ST_Within
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hermes_db.enums import EventScope, EventStatus, SelectionTier
from hermes_db.models.article import Article
from hermes_db.models.event import Event
from hermes_db.models.thread import Thread


logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_events(
        self,
        status: EventStatus | None = EventStatus.ACTIVE,
        scope: EventScope | None = None,
        limit: int = 50,
    ) -> list[Event]:
        stmt = select(Event).options(selectinload(Event.thread))
        if status:
            stmt = stmt.where(Event.status == status)
        if status == EventStatus.ACTIVE:
            stmt = stmt.where(Event.selection_tier != SelectionTier.DROP)
            stmt = stmt.where(Event.merged_into_id.is_(None))
        if scope:
            stmt = stmt.where(Event.scope == scope)
        stmt = stmt.order_by(
            Event.importance_score.desc(),
            Event.first_reported_at.desc(),
        ).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_events_by_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        limit: int = 200,
    ):
        bbox_poly = ST_MakeEnvelope(west, south, east, north, 4326)
        stmt = (
            select(
                Event,
                ST_X(Event.location).label("longitude"),
                ST_Y(Event.location).label("latitude"),
                Thread.name.label("thread_name"),
            )
            .outerjoin(Thread, Thread.id == Event.thread_id)
            .where(Event.location.isnot(None))
            .where(ST_Within(Event.location, bbox_poly))
            .where(Event.status == EventStatus.ACTIVE)
            .where(Event.selection_tier != SelectionTier.DROP)
            .where(Event.merged_into_id.is_(None))
            .order_by(Event.importance_score.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.all()

    async def get_event_by_id(self, event_id: uuid.UUID) -> Event | None:
        current = event_id
        seen: set[uuid.UUID] = set()
        while current not in seen:
            seen.add(current)
            stmt = (
                select(Event)
                .options(
                    selectinload(Event.articles).joinedload(Article.source),
                    selectinload(Event.thread),
                )
                .where(Event.id == current)
            )
            event = (await self._session.execute(stmt)).scalar_one_or_none()
            if event is None:
                return None
            if event.merged_into_id is None:
                return event
            current = event.merged_into_id
        logger.warning("merge redirect cycle detected for event %s.", event_id)
        return None

    async def get_active_events(self) -> list[dict[str, str]]:
        stmt = (
            select(
                Event.id,
                Event.ai_headline,
                Event.location_name,
                Event.category,
            )
            .where(Event.status == EventStatus.ACTIVE)
            .where(Event.selection_tier != SelectionTier.DROP)
            .where(Event.merged_into_id.is_(None))
            .order_by(Event.importance_score.desc())
            .limit(100)
        )
        result = await self._session.execute(stmt)
        return [
            {
                "id": str(event_id),
                "headline": headline,
                "location_name": location_name or "N/A",
                "category": category,
            }
            for event_id, headline, location_name, category in result.all()
        ]

    async def get_active_events_by_embeddings(
        self, embeddings: Sequence[Sequence[float] | None]
    ) -> list[dict[str, str]]:
        if not embeddings:
            return []
        unique_events: dict[str, dict[str, str]] = {}
        for emb in embeddings:
            if not emb:
                continue
            stmt = (
                select(
                    Event.id,
                    Event.ai_headline,
                    Event.location_name,
                    Event.category,
                )
                .where(Event.status == EventStatus.ACTIVE)
                .where(Event.merged_into_id.is_(None))
                .where(Event.embedding.is_not(None))
                .where(Event.embedding.cosine_distance(emb) < 0.25)
                .order_by(Event.embedding.cosine_distance(emb))
                .limit(5)
            )
            result = await self._session.execute(stmt)
            for event_id, headline, location_name, category in result.all():
                row_id = str(event_id)
                if row_id not in unique_events:
                    unique_events[row_id] = {
                        "id": row_id,
                        "headline": headline,
                        "location_name": location_name or "N/A",
                        "category": category,
                    }

        return list(unique_events.values())
