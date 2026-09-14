import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.db.enums import CredibilityTier
from hermes_api.db.models.article import Article
from hermes_api.db.models.event import Event
from hermes_api.db.models.source import Source
from hermes_api.services.ai_service import TimelineEvent
from hermes_api.services.geocoding_service import GeocodingService

logger = logging.getLogger(__name__)


class LineageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._geocoding = GeocodingService()

    async def get_or_create_wikipedia_source(self) -> Source:
        """Ensure a Wikipedia source exists for attribution."""
        stmt = select(Source).where(Source.name == "Wikipedia")
        result = await self._session.execute(stmt)
        source = result.scalar_one_or_none()
        if not source:
            source = Source(
                name="Wikipedia",
                feed_url="https://en.wikipedia.org",
                credibility=CredibilityTier.TIER_1,
                is_active=False,  # Not used for RSS ingestion
            )
            self._session.add(source)
            await self._session.flush()
        return source

    def _parse_timeline_date(self, date_str: str) -> datetime:
        """Parse YYYY-MM-DD, YYYY-MM, or YYYY into a datetime."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not date_str:
            return now
        try:
            parts = date_str.split("-")
            if len(parts) == 3:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            elif len(parts) == 2:
                return datetime(int(parts[0]), int(parts[1]), 1)
            elif len(parts) == 1:
                return datetime(int(parts[0]), 1, 1)
        except Exception:
            pass
        return now

    async def persist_lineage_events(
        self,
        target_event_id: uuid.UUID,
        events: list[TimelineEvent],
        page_title: str,
    ) -> list[Event]:
        """Geocode and persist historical timeline events.

        Args:
            target_event_id: The UUID of the root story event.
            events: Extracted structured historical events.
            page_title: Wikipedia page title for attribution link.

        Returns:
            The list of newly created Event models.
        """
        if not events:
            return []

        wiki_source = await self.get_or_create_wikipedia_source()
        article_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"

        persisted_events = []
        for tl_event in events:
            # 1. Geocode
            geocoding = None
            if tl_event.location_name:
                geocoding = await self._geocoding.geocode(self._session, tl_event.location_name)

            location_wkt = None
            if geocoding:
                location_wkt = f"SRID=4326;POINT({geocoding.longitude} {geocoding.latitude})"

            event_date = self._parse_timeline_date(tl_event.date)
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # 2. Persist Event
            event = Event(
                ai_headline=tl_event.headline,
                ai_summary=tl_event.summary,
                category="HISTORICAL",
                category_color="#808080",  # Gray for historical/context events
                location=location_wkt,
                location_name=tl_event.location_name,
                trending_score=1.0,
                article_count=1,
                first_reported_at=event_date,
                last_updated_at=now,
                lineage_target_id=target_event_id,
            )
            self._session.add(event)
            await self._session.flush()

            # 3. Persist Article (for attribution)
            article = Article(
                event_id=event.id,
                source_id=wiki_source.id,
                title=f"{page_title}: {tl_event.headline}",
                url=f"{article_url}#{event.id}",  # unique constraint workaround if multiple events from same page
                published_at=event_date,
            )
            self._session.add(article)
            persisted_events.append(event)

        await self._session.commit()
        logger.info(
            f"persisted {len(persisted_events)} lineage events "
            f"for target {target_event_id} from Wikipedia '{page_title}'."
        )
        return persisted_events
