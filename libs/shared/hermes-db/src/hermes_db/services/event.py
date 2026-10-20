import logging
import math
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from geoalchemy2.functions import ST_X, ST_Y, ST_MakeEnvelope, ST_Within
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hermes_db.core.config import settings
from hermes_db.enums import (
    CredibilityTier,
    EventScope,
    EventStatus,
    GeopoliticalBloc,
    ImpactLevel,
)
from hermes_db.models.article import Article
from hermes_db.models.event import Event
from hermes_db.models.source import Source
from hermes_db.protocols import EventExtractionData, GeocodingData
from hermes_db.services.article import ArticleService
from hermes_db.services.ranking import (
    CREDIBILITY_WEIGHTS,
    HALF_LIFE_HOURS,
    HOURLY_DECAY_FACTOR,
    IMPACT_MULTIPLIERS,
    SOURCE_BLOC_MAP,
    calculate_shannon_diversity,
    calculate_velocity,
    calculate_velocity_multiplier,
)


__all__ = [
    "CREDIBILITY_WEIGHTS",
    "HALF_LIFE_HOURS",
    "HOURLY_DECAY_FACTOR",
    "IMPACT_MULTIPLIERS",
    "SOURCE_BLOC_MAP",
    "EventExtractionData",
    "EventService",
    "GeocodingData",
    "calculate_shannon_diversity",
    "calculate_velocity",
    "calculate_velocity_multiplier",
]


logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._article_service = ArticleService(session)

    async def create_event_with_article(
        self,
        extraction: EventExtractionData,
        geocoding: GeocodingData | None,
        article_title: str,
        article_url: str,
        source_id: uuid.UUID,
        source_credibility: CredibilityTier,
        published_at: datetime | None = None,
        embedding: list[float] | None = None,
    ) -> Event | None:
        location_wkt = None
        if geocoding:
            location_wkt = (
                f"SRID=4326;POINT({geocoding.longitude} {geocoding.latitude})"
            )

        now = datetime.now(UTC).replace(tzinfo=None)
        raw_impact = getattr(extraction, "impact_level", ImpactLevel.MODERATE)
        impact = (
            ImpactLevel(raw_impact)
            if isinstance(raw_impact, str)
            else (raw_impact or ImpactLevel.MODERATE)
        )
        impact_mult = IMPACT_MULTIPLIERS.get(impact, 1.0)
        base_score = CREDIBILITY_WEIGHTS.get(source_credibility, 1.0)
        initial_score = base_score * impact_mult

        event = Event(
            ai_headline=extraction.headline,
            ai_summary=extraction.summary,
            category=extraction.category,
            category_color=extraction.category_color,
            impact_level=impact,
            location=location_wkt,
            location_name=extraction.location_name,
            embedding=embedding,
            trending_score=initial_score,
            velocity=1.0,
            article_count=1,
            first_reported_at=now,
            last_updated_at=now,
        )
        self._session.add(event)
        await self._session.flush()

        article = await self._article_service.create_article(
            event_id=event.id,
            source_id=source_id,
            title=article_title,
            url=article_url,
            published_at=published_at,
        )
        if article is None:
            await self._session.rollback()
            logger.info(
                "duplicate article url for new event '%s', rolling back.",
                event.ai_headline,
            )
            return None

        await self._session.commit()

        logger.info("created event '%s' with 1 article.", event.ai_headline)
        return event


    async def add_article_to_event(
        self,
        event_id: uuid.UUID,
        article_title: str,
        article_url: str,
        source_id: uuid.UUID,
        source_credibility: CredibilityTier,
        published_at: datetime | None = None,
    ) -> Event | None:
        event = await self._session.get(Event, event_id)
        if not event:
            logger.warning("event not found for event id: %s.", event_id)
            return None

        article = await self._article_service.create_article(
            event_id=event.id,
            source_id=source_id,
            title=article_title,
            url=article_url,
            published_at=published_at,
        )
        if article is None:
            logger.info(
                "duplicate article url for event '%s', skipping score update.",
                event.ai_headline,
            )
            return None

        event.article_count += 1
        now = datetime.now(UTC).replace(tzinfo=None)
        event.last_updated_at = now

        # query sources for syndication count and geopolitical bloc diversity.
        stmt = (
            select(Source.id, Source.slug)
            .join(Article, Article.source_id == Source.id)
            .where(Article.event_id == event.id)
        )
        result = await self._session.execute(stmt)
        source_rows = result.all()

        n = sum(1 for sid, _ in source_rows if sid == source_id)
        if n <= 0:
            n = 1
        syndication_factor = 1.0 / math.sqrt(n)

        blocs = [
            SOURCE_BLOC_MAP.get(slug, GeopoliticalBloc.GLOBAL_WIRE)
            for _, slug in source_rows
            if slug
        ]
        diversity = calculate_shannon_diversity(blocs)

        first_reported = getattr(event, "first_reported_at", None)
        if isinstance(first_reported, datetime):
            event.velocity = calculate_velocity(
                event.article_count, first_reported, now
            )
        else:
            event.velocity = 1.0

        vel_mult = calculate_velocity_multiplier(event.velocity)

        raw_impact = getattr(event, "impact_level", ImpactLevel.MODERATE)
        impact = (
            ImpactLevel(raw_impact)
            if isinstance(raw_impact, str)
            else (raw_impact or ImpactLevel.MODERATE)
        )
        impact_mult = IMPACT_MULTIPLIERS.get(impact, 1.0)

        base_credibility = CREDIBILITY_WEIGHTS.get(source_credibility, 1.0)
        added_score = (
            base_credibility * syndication_factor * impact_mult * diversity * vel_mult
        )
        event.trending_score += added_score

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
            select(Event)
            .options(selectinload(Event.articles).joinedload(Article.source))
            .where(Event.id == event_id)
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

        # decay event scores using continuous exponential half-life (18h half-life).
        decay_stmt = (
            update(Event)
            .where(Event.status == EventStatus.ACTIVE)
            .values(trending_score=Event.trending_score * HOURLY_DECAY_FACTOR)
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
