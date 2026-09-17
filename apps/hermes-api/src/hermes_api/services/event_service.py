import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.core.config import settings
from hermes_api.db.enums import CredibilityTier, EventStatus
from hermes_api.db.models.article import Article
from hermes_api.db.models.event import Event
from hermes_api.services.ai_service import ExtractedEvent
from hermes_api.services.geocoding_service import GeocodingResult

logger = logging.getLogger(__name__)

CREDIBILITY_WEIGHTS = {
    CredibilityTier.TIER_1: 3.0,
    CredibilityTier.TIER_2: 2.0,
    CredibilityTier.TIER_3: 1.0,
    CredibilityTier.TIER_4: 0.5,
}







class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session




    # create.
    async def create_event_with_article(
        self,
        extraction: ExtractedEvent,
        geocoding: Optional[GeocodingResult],
        article_title: str,
        article_url: str,
        source_id: uuid.UUID,
        source_credibility: CredibilityTier,
        published_at: Optional[datetime] = None,
        embedding: Optional[list[float]] = None,
    ) -> Event:
        location_wkt = None
        if geocoding:
            location_wkt = (
                f"SRID=4326;POINT({geocoding.longitude} {geocoding.latitude})"
            )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        initial_score = CREDIBILITY_WEIGHTS.get(source_credibility, 1.0)

        event = Event(
            ai_headline=extraction.headline,
            ai_summary=extraction.summary,
            category=extraction.category,
            category_color=extraction.category_color,
            location=location_wkt,
            location_name=extraction.location_name,
            embedding=embedding,
            trending_score=initial_score,
            article_count=1,
            first_reported_at=now,
            last_updated_at=now,
        )
        self._session.add(event)
        await self._session.flush()

        article = Article(
            event_id=event.id,
            source_id=source_id,
            title=article_title,
            url=article_url,
            published_at=published_at,
        )
        self._session.add(article)
        await self._session.commit()

        logger.info(f"created event '{event.ai_headline}' with 1 article.")
        return event




    # update.
    async def add_article_to_event(
        self,
        event_id: uuid.UUID,
        article_title: str, article_url: str,
        source_id: uuid.UUID, source_credibility: CredibilityTier,
        published_at: Optional[datetime] = None,
    ) -> Optional[Event]:
        event = await self._session.get(Event, event_id)
        if not event:
            logger.warning(f"event not found for event id: {event_id}.")
            return None

        article = Article(
            event_id=event.id,
            source_id=source_id,
            title=article_title,
            url=article_url,
            published_at=published_at,
        )
        self._session.add(article)

        event.article_count += 1
        added_score = CREDIBILITY_WEIGHTS.get(source_credibility, 1.0)
        event.trending_score += added_score

        event.last_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if event.status == EventStatus.STALE:
            event.status = EventStatus.ACTIVE
            logger.info(f"reactivated stale event: '{event.ai_headline}'.")

        await self._session.commit()
        logger.info(
            f"added article to event '{event.ai_headline}' (now {event.article_count} articles)."
        )

        return event




    @staticmethod
    def _to_event_dict(row) -> dict[str, str]:
        return {
            "id": str(row.id),
            "headline": row.ai_headline,
            "location_name": row.location_name or "N/A",
            "category": row.category,
        }


    # queries (used by the ai service and api layer).
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
        return [self._to_event_dict(row) for row in result.all()]




    async def get_active_events_by_embeddings(self, embeddings: list[list[float]]) -> list[dict[str, str]]:
        if not embeddings:
            return []

        unique_events = {}
        for emb in embeddings:
            if not emb:
                continue

            # cosine distance to get events.
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
            for row in result.all():
                row_id = str(row.id)
                if row_id not in unique_events:
                    unique_events[row_id] = self._to_event_dict(row)

        return list(unique_events.values())




    # check whether the article was already processed.
    async def article_url_exists(self, url: str) -> bool:
        stmt = select(Article.id).where(Article.url == url).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None




    async def _transition_event_status(self, from_status: EventStatus, to_status: EventStatus, cutoff: datetime) -> int:
        stmt = (
            update(Event)
            .where(Event.status == from_status)
            .where(Event.last_updated_at < cutoff)
            .values(status=to_status)
        )
        result = await self._session.execute(stmt)
        return result.rowcount


    # lifecycle management for events.
    async def run_lifecycle_transitions(self) -> dict[str, int]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stale_cutoff = now - timedelta(hours=settings.EVENT_STALE_HOURS)
        archive_cutoff = now - timedelta(hours=settings.EVENT_ARCHIVE_HOURS)

        # decay active event scores by 10% every time this runs.
        decay_stmt = (
            update(Event)
            .where(Event.status == EventStatus.ACTIVE)
            .values(trending_score=Event.trending_score * 0.90)
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
            logger.info(f"lifecycle: {staled_count} events staled, {archived_count} events archived.")

        return { "staled": staled_count, "archived": archived_count }
