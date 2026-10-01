import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_X, ST_Y, ST_MakeEnvelope, ST_Within

from hermes_db.core.config import settings
from hermes_db.enums import CredibilityTier, EventScope, EventStatus
from hermes_db.models.event import Event
from hermes_db.services.article import ArticleService


logger = logging.getLogger(__name__)

CREDIBILITY_WEIGHTS = {
    CredibilityTier.TIER_1: 3.0,
    CredibilityTier.TIER_2: 2.0,
    CredibilityTier.TIER_3: 1.0,
    CredibilityTier.TIER_4: 0.5,
}


class EventExtractionData(Protocol):
    headline: str
    summary: str
    category: str
    category_color: str | None
    location_name: str | None


class GeocodingData(Protocol):
    latitude: float
    longitude: float





class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._article_service = ArticleService(session)



    async def create_event_with_article(
        self,
        extraction: EventExtractionData,
        geocoding: GeocodingData | None,
        article_title: str, article_url: str,
        source_id: uuid.UUID, source_credibility: CredibilityTier,
        published_at: datetime | None = None,
        embedding: list[float] | None = None,
    ) -> Event:
        location_wkt = None
        if geocoding:
            location_wkt = (
                f"SRID=4326;POINT({geocoding.longitude} {geocoding.latitude})"
            )

        now = datetime.now(UTC).replace(tzinfo=None)
        initial_score = CREDIBILITY_WEIGHTS.get(source_credibility, 1.0)

        event = Event(
            ai_headline=extraction.headline, ai_summary=extraction.summary,
            category=extraction.category, category_color=extraction.category_color,
            location=location_wkt, location_name=extraction.location_name,
            embedding=embedding,
            trending_score=initial_score, article_count=1,
            first_reported_at=now, last_updated_at=now,
        )
        self._session.add(event)
        await self._session.flush()

        await self._article_service.create_article(
            event_id=event.id,
            source_id=source_id,
            title=article_title,
            url=article_url,
            published_at=published_at,
        )
        await self._session.commit()

        logger.info("created event '%s' with 1 article.", event.ai_headline)
        return event



    async def add_article_to_event(
        self,
        event_id: uuid.UUID,
        article_title: str, article_url: str,
        source_id: uuid.UUID, source_credibility: CredibilityTier,
        published_at: datetime | None = None,
    ) -> Event | None:
        event = await self._session.get(Event, event_id)
        if not event:
            logger.warning("event not found for event id: %s.", event_id)
            return None

        await self._article_service.create_article(
            event_id=event.id,
            source_id=source_id,
            title=article_title,
            url=article_url,
            published_at=published_at,
        )

        event.article_count += 1
        added_score = CREDIBILITY_WEIGHTS.get(source_credibility, 1.0)
        event.trending_score += added_score
        event.last_updated_at = datetime.now(UTC).replace(tzinfo=None)
        if event.status == EventStatus.STALE:
            event.status = EventStatus.ACTIVE
            logger.info("reactivated stale event: '%s'.", event.ai_headline)

        await self._session.commit()
        logger.info(
            "added article to event '%s' (now %s articles).",
            event.ai_headline,
            event.article_count,
        )
        return event



    async def get_events(
        self,
        status: EventStatus | None = EventStatus.ACTIVE,
        scope: EventScope | None = None,
        limit: int = 50,
    ) -> list[Event]:
        stmt = select(Event)
        if status:
            stmt = stmt.where(Event.status == status)
        if scope:
            stmt = stmt.where(Event.scope == scope)

        stmt = stmt.order_by(Event.trending_score.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())



    async def get_events_by_bbox(
        self, north: float, south: float, east: float, west: float
    ):
        bbox_poly = ST_MakeEnvelope(west, south, east, north, 4326)
        stmt = (
            select(
                Event,
                ST_X(Event.location).label("longitude"),
                ST_Y(Event.location).label("latitude"),
            )
            .where(Event.location.isnot(None))
            .where(ST_Within(Event.location, bbox_poly))
            .where(Event.status == EventStatus.ACTIVE)
            .order_by(Event.trending_score.desc())
            .limit(200)
        )
        result = await self._session.execute(stmt)
        return result.all()



    async def get_event_by_id(self, event_id: uuid.UUID) -> Event | None:
        stmt = (
            select(Event).options(selectinload(Event.articles)).where(Event.id == event_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()



    async def get_active_events(self) -> list[dict[str, str]]:
        stmt = (
            select(
                Event.id,
                Event.ai_headline,
                Event.location_name,
                Event.category,
            )
            .where(Event.status == EventStatus.ACTIVE)
            .order_by(Event.trending_score.desc())
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



    async def get_active_events_by_embeddings(self, embeddings: list[list[float]]) -> list[dict[str, str]]:
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



    async def article_url_exists(self, url: str) -> bool:
        return await self._article_service.article_url_exists(url)



    async def _transition_event_status(
        self, from_status: EventStatus, to_status: EventStatus, cutoff: datetime
    ) -> int:
        stmt = (
            update(Event)
            .where(Event.status == from_status)
            .where(Event.last_updated_at < cutoff)
            .values(status=to_status)
        )
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0

    async def run_lifecycle_transitions(self) -> dict[str, int]:
        now = datetime.now(UTC).replace(tzinfo=None)
        stale_cutoff = now - timedelta(hours=settings.EVENT_STALE_HRS)
        archive_cutoff = now - timedelta(hours=settings.EVENT_ARCHIVE_HRS)

        # decay event scores by 10%.
        decay_stmt = (
            update(Event)
            .where(Event.status == EventStatus.ACTIVE)
            .values(trending_score=Event.trending_score * 0.9)
        )
        await self._session.execute(decay_stmt)
        staled_count = await self._transition_event_status(
            EventStatus.ACTIVE, EventStatus.STALE, stale_cutoff
        )
        archived_count = await self._transition_event_status(
            EventStatus.STALE, EventStatus.ARCHIVED, archive_cutoff
        )

        await self._session.commit()
        if staled_count or archived_count:
            logger.info(
                "lifecycle: %s events staled, %s events archived.",
                staled_count,
                archived_count,
            )
        return {"staled": staled_count, "archived": archived_count}
