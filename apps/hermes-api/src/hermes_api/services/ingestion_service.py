import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.core.config import settings
from hermes_api.core.rate_limiter import TokenBucketRateLimiter
from hermes_api.db.db import AsyncSessionLocal
from hermes_api.db.models.source import Source
from hermes_api.services.ai_service import (
    EXTRACTION_BATCH_SIZE,
    AiService,
    ArticleInput,
)
from hermes_api.services.event_service import EventService
from hermes_api.services.geocoding_service import GeocodingService
from hermes_api.services.rss_service import ParsedArticle, fetch_feed

logger = logging.getLogger(__name__)





class IngestionService:
    def __init__(self) -> None:
        self._ai = AiService()
        self._geocoding = GeocodingService()
        self._rate_limiter = TokenBucketRateLimiter(settings.GEMINI_RPM_LIMIT)

    
    async def _ingest_source(self, source: dict) -> dict[str, int]:
        """Ingest a single RSS source: fetch, dedup, batch-extract, persist.

        Args:
            source: Dict with 'id', 'name', and 'feed_url' keys.

        Returns:
            A stats dict with counts of fetched, skipped, processed,
            failed, created, and matched articles.
        """
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

        # Phase 1: Filter out already-processed article URLs.
        articles_to_process: list[ParsedArticle] = []
        async with AsyncSessionLocal() as session:
            event_service = EventService(session)
            for article in articles:
                if await event_service.article_url_exists(article.url):
                    stats["articles_skipped_duplicate"] += 1
                else:
                    articles_to_process.append(article)

        if not articles_to_process:
            logger.info(
                f"source '{source_name}': all "
                f"{len(articles)} articles already processed."
            )
            return stats

        # Phase 2: Batch AI extraction — one LLM call per batch.
        for batch_start in range(
            0, len(articles_to_process), EXTRACTION_BATCH_SIZE
        ):
            batch = articles_to_process[
                batch_start:batch_start + EXTRACTION_BATCH_SIZE
            ]

            ai_inputs = [
                ArticleInput(
                    title=article.title,
                    content=article.text_for_ai,
                )
                for article in batch
            ]
            
            # Semantic Pre-filtering
            # Generate embeddings for the new articles
            batch_texts = [f"{a.title}\n{a.text_for_ai}" for a in batch]
            embeddings = await self._ai.generate_embeddings_batch(batch_texts)

            # Find semantically similar active events
            async with AsyncSessionLocal() as session:
                event_service = EventService(session)
                existing_events = (
                    await event_service.get_active_events_by_embeddings(embeddings)
                )

            await self._rate_limiter.acquire()
            extractions = await self._ai.extract_metadata_batch(
                articles=ai_inputs,
                existing_events=existing_events,
            )

            # Phase 3: Geocode and persist each result individually.
            for i, extraction in enumerate(extractions):
                article = batch[i]
                article_embedding = embeddings[i] if i < len(embeddings) else None
                if not extraction:
                    stats["articles_failed"] += 1
                    continue

                try:
                    async with AsyncSessionLocal() as session:
                        event_service = EventService(session)

                        geocoding = None
                        if (
                            extraction.has_location
                            and extraction.location_name
                        ):
                            geocoding = await self._geocoding.geocode(
                                session, extraction.location_name,
                            )

                        if extraction.matched_event_id:
                            matched = (
                                await event_service.add_article_to_event(
                                    event_id=uuid.UUID(
                                        extraction.matched_event_id,
                                    ),
                                    article_title=article.title,
                                    article_url=article.url,
                                    source_id=source_id,
                                    published_at=article.published_at,
                                )
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
                                    embedding=article_embedding,
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
                                embedding=article_embedding,
                            )
                            stats["events_created"] += 1
                        stats["articles_processed"] += 1
                except Exception:
                    logger.exception(
                        f"failed to process article: {article.title}."
                    )
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
            select(
                Source.id,
                Source.name,
                Source.feed_url,
                Source.last_fetched_at,
                Source.fetch_interval_minutes,
            )
            .where(Source.is_active.is_(True))
            .where(Source.feed_url.isnot(None))
        )
        result = await session.execute(stmt)
        rows = result.all()
        
        due_sources = []
        now = datetime.now(timezone.utc)
        
        for row in rows:
            if not row.last_fetched_at:
                due_sources.append({
                    "id": row.id, 
                    "name": row.name, 
                    "feed_url": row.feed_url
                })
                continue
                
            last = row.last_fetched_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
                
            delta = timedelta(minutes=row.fetch_interval_minutes)
            if now >= last + delta:
                due_sources.append({
                    "id": row.id, 
                    "name": row.name, 
                    "feed_url": row.feed_url
                })
                
        return due_sources



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
        
        semaphore = asyncio.Semaphore(5)

        async def _process_source(source: dict) -> dict[str, int]:
            async with semaphore:
                try:
                    s_stats = await self._ingest_source(source)
                    # Record that this source was just fetched
                    async with AsyncSessionLocal() as db_session:
                        await db_session.execute(
                            update(Source)
                            .where(Source.id == source["id"])
                            .values(last_fetched_at=func.now())
                        )
                        await db_session.commit()
                    return s_stats
                except Exception:
                    logger.exception(
                        f"Unhandled error ingesting source {source['name']}"
                    )
                    # Return empty stats so the aggregator doesn't crash
                    return {k: 0 for k in stats if k != "sources_processed"}
                    
        tasks = [_process_source(s) for s in sources]
        results = await asyncio.gather(*tasks)
        
        for source_stats in results:
            for key in source_stats:
                if key in stats:
                    stats[key] += source_stats[key]
            stats["sources_processed"] += 1

        logger.info(
            f"ingestion complete: {stats['sources_processed']} sources, "
            f"{stats['articles_processed']} articles processed, "
            f"{stats['events_created']} new events, "
            f"{stats['events_matched']} matched to existing"
        )
        return stats