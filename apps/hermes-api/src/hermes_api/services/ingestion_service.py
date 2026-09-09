import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.core.config import settings
from hermes_api.core.rate_limiter import TokenBucketRateLimiter
from hermes_api.db.db import AsyncSessionLocal
from hermes_api.db.models.source import Source
from hermes_api.services.ai_service import AiService
from hermes_api.services.event_service import EventService
from hermes_api.services.geocoding_service import GeocodingService
from hermes_api.services.rss_service import fetch_feed

logger = logging.getLogger(__name__)





class IngestionService:
    def __init__(self) -> None:
        self._ai = AiService()
        self._geocoding = GeocodingService()
        self._rate_limiter = TokenBucketRateLimiter(settings.GEMINI_RPM_LIMIT)

    
    async def _ingest_source(self, source: dict) -> dict[str, int]:
        stats = {
            "articles_fetched": 0,
            "articles_skipped_duplicate": 0,
            "articles_processed": 0,
            "articles_failed": 0,
            "events_created": 0,
            "events_matched": 0,
        }
        feed_url = source["feed_url"]
        source_id = source["id"]
        source_name = source["name"]

        logger.info(f"ingesting source: {source_name} {feed_url}.")
        articles = await fetch_feed(feed_url)
        stats["articles_fetched"] = len(articles)
        if not articles:
            return stats
        else:
            for article in articles:
                try:
                    async with AsyncSessionLocal() as session:
                        event_service = EventService(session)
                        
                        if await event_service.article_url_exists(article.url):
                            stats["articles_skipped_duplicate"] += 1
                            continue
                        
                        existing_events = (
                            await event_service.get_active_events_for_matching()
                        )
                        await self._rate_limiter.acquire()
                        extraction = await self._ai.extract_metadata(
                            title=article.title,
                            content=article.text_for_ai,
                            existing_events=existing_events,
                        )
                        if not extraction:
                            stats["articles_failed"] += 1
                            continue
                        geocoding = None
                        if extraction.has_location and extraction.location_name:
                            geocoding = await self._geocoding.geocode(
                                extraction.location_name,
                            )
                        
                        if extraction.matched_event_id:
                            matched = await event_service.add_article_to_event(
                                event_id=uuid.UUID(extraction.matched_event_id),
                                article_title=article.title,
                                article_url=article.url,
                                source_id=source_id,
                                published_at=article.published_at,
                            )
                            if matched:
                                stats["events_matched"] += 1
                            else:
                                await event_service.create_event_with_article(
                                    extraction=extraction,
                                    geocoding=geocoding,
                                    article_title=article.title,
                                    article_url=article.url,
                                    source_id=source_id,
                                    published_at=article.published_at,
                                )
                                stats["events_created"] += 1
                        else:
                            await event_service.create_event_with_article(
                                extraction=extraction,
                                geocoding=geocoding,
                                article_title=article.title,
                                article_url=article.url,
                                source_id=source_id,
                                published_at=article.published_at,
                            )
                            stats["events_created"] += 1
                        stats["articles_processed"] += 1
                except Exception:
                    logger.exception(f"failed to process article: {article.title}.")
                    stats["articles_failed"] += 1
    
        logger.info(
            f"finished source '{source_name}': "
            f"{stats['articles_processed']} processed, "
            f"{stats['articles_skipped_duplicate']} skipped (duplicates), "
            f"{stats['articles_failed']} failed"
        )
        return stats



    async def _get_active_sources(self, session: AsyncSession) -> list[dict]:
        stmt = (
            select(Source.id, Source.name, Source.feed_url)
            .where(Source.is_active.is_(True))
            .where(Source.feed_url.isnot(None))
        )
        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "feed_url": row.feed_url,
            }
            for row in rows
        ]



    async def ingest_all_sources(self) -> dict[str, int]:
        stats = {
            "sources_processed": 0,
            "articles_fetched": 0,
            "articles_skipped_duplicate": 0,
            "articles_processed": 0,
            "articles_failed": 0,
            "events_created": 0,
            "events_matched": 0,
        }

        async with AsyncSessionLocal() as session:
            sources = await self._get_active_sources(session)
        if not sources:
            logger.warning("no active sources found in the database.")
            return stats

        logger.info(f"starting ingestion for {len(sources)} sources.")
        for source in sources:
            source_stats = await self._ingest_source(source)
            for key in source_stats:
                stats[key] = stats.get(key, 0) + source_stats[key]
            stats["sources_processed"] += 1

        logger.info(
            f"ingestion complete: {stats['sources_processed']} sources, "
            f"{stats['articles_processed']} articles processed, "
            f"{stats['events_created']} new events, "
            f"{stats['events_matched']} matched to existing"
        )
        return stats