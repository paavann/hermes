import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.db.enums import CredibilityTier
from hermes_api.db.models.article import Article
from hermes_api.db.models.event import Event
from hermes_api.db.models.event_edge import EventEdge
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
                slug="wikipedia",
                url="https://en.wikipedia.org",
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
                geocoding = await self._geocoding.geocode(
                    self._session, tl_event.location_name
                )

            location_wkt = None
            if geocoding:
                location_wkt = (
                    f"SRID=4326;POINT({geocoding.longitude} {geocoding.latitude})"
                )

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

            # 4. Persist Edge (link lineage event to target event)
            edge = EventEdge(
                event_a_id=event.id,
                event_b_id=target_event_id,
                relationship_type="related",
                confidence=1.0,
            )
            self._session.add(edge)

            persisted_events.append(event)

        await self._session.commit()
        logger.info(
            f"persisted {len(persisted_events)} lineage events "
            f"for target {target_event_id} from Wikipedia '{page_title}'."
        )
        return persisted_events

    async def sync_allowlisted_stories(self) -> dict:
        """Finds all allowlisted events that don't have lineage processed, and generates them."""
        from sqlalchemy import text
        from hermes_api.services.wikipedia_service import fetch_page_extracts
        from hermes_api.services.ai_service import AiService, ArticleInput

        stmt = text("""
            SELECT sa.event_id, sa.wikipedia_page_title 
            FROM story_allowlists sa
            LEFT JOIN event_edges ee ON sa.event_id = ee.event_b_id OR sa.event_id = ee.event_a_id
            WHERE ee.id IS NULL
        """)
        result = await self._session.execute(stmt)
        rows = result.all()

        if not rows:
            return {"status": "no new stories to sync"}

        ai = AiService()
        stats = {"processed": 0, "nodes_created": 0, "errors": 0}

        for row in rows:
            event_id = row.event_id
            page_title = row.wikipedia_page_title

            logger.info(f"Syncing lineage for event {event_id} from {page_title}...")
            try:
                extracts = await fetch_page_extracts([page_title])
                content = extracts.get(page_title, "")
                if not content:
                    logger.warning(f"No content for {page_title}")
                    stats["errors"] += 1
                    continue

                # Limit to 5000 chars for processing speed/token limits during syncing
                batch_nodes = await ai.extract_timeline_events_batch(
                    [ArticleInput(title=page_title, content=content[:5000])]
                )
                nodes = batch_nodes[0] if batch_nodes else []

                events = await self.persist_lineage_events(event_id, nodes, page_title)
                stats["processed"] += 1
                stats["nodes_created"] += len(events)
            except Exception as e:
                logger.error(f"Failed to sync lineage for {event_id}: {e}")
                stats["errors"] += 1

        return stats
