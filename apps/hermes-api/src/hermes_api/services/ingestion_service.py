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
from hermes_api.services.ai_service import ARTICLE_BATCH_SIZE, AiService, ArticleInput
from hermes_api.services.event_service import EventService
from hermes_api.services.geocoding_service import GeocodingService
from hermes_api.services.rss_service import ParsedArticle, fetch_feed

logger = logging.getLogger(__name__)







class IngestionService:
    def __init__(self) -> None:
        self._ai = AiService()
        self._geocoding = GeocodingService()
        self._rate_limiter = TokenBucketRateLimiter(settings.RPM_LIMIT)
        self._embed_rate_limiter = TokenBucketRateLimiter(settings.EMBED_RPM_LIMIT)




    async def _ingest_source(self, source: dict) -> dict[str, int]:
        stats = {
            "articles_fetched": 0,
            "articles_skipped": 0,
            "articles_processed": 0,
            "articles_failed": 0,
            "events_created": 0,
            "events_matched": 0,
        }
        feed_url = source["feed_url"]
        source_id = source["id"]
        source_name = source["name"]

        logger.info("ingesting source: %s - %s.", source_name, feed_url)
        articles = await fetch_feed(feed_url)
        stats["articles_fetched"] = len(articles)
        if not articles:
            logger.info("no articles found in %s.", source_name)
            return stats
        else:
            articles_to_process: list[ParsedArticle] = []
            async with AsyncSessionLocal() as session:
                event_service = EventService(session)
                for article in articles:
                    if await event_service.article_url_exists(article.url):
                        stats["articles_skipped"] += 1
                    else:
                        articles_to_process.append(article)

        if not articles_to_process:
            logger.info(
                "source '%s': all %s articles already processed.",
                source_name,
                len(articles),
            )
            return stats
        else:
            for batch_start in range(0, len(articles_to_process), ARTICLE_BATCH_SIZE):
                batch = articles_to_process[
                    batch_start : batch_start + ARTICLE_BATCH_SIZE
                ]
                ai_inputs = [
                    ArticleInput(
                        title=article.title,
                        content=article.text_for_ai,
                    )
                    for article in batch
                ]

                batch_texts = [f"{a.title}\n{a.text_for_ai}" for a in batch]
                await self._embed_rate_limiter.acquire()
                embeddings = await self._ai.gen_embeddings(batch_texts)

                async with AsyncSessionLocal() as session:
                    event_service = EventService(session)
                    existing_events = (
                        await event_service.get_active_events_by_embeddings(embeddings)
                    )

                await self._rate_limiter.acquire()
                extractions = await self._ai.get_metadata(
                    articles=ai_inputs,
                    existing_events=existing_events,
                )

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
                            if extraction.has_location and extraction.location_name:
                                geocoding = await self._geocoding.geocode(
                                    session,
                                    extraction.location_name,
                                )

                            matched = False
                            if extraction.matched_event_id:
                                matched = await event_service.add_article_to_event(
                                    event_id=uuid.UUID(extraction.matched_event_id),
                                    article_title=article.title,
                                    article_url=article.url,
                                    source_id=source_id,
                                    source_credibility=source["credibility"],
                                    published_at=article.published_at,
                                )
                                if matched:
                                    stats["events_matched"] += 1

                            if not matched:
                                await event_service.create_event_with_article(
                                    extraction=extraction,
                                    geocoding=geocoding,
                                    article_title=article.title,
                                    article_url=article.url,
                                    source_id=source_id,
                                    source_credibility=source["credibility"],
                                    published_at=article.published_at,
                                    embedding=article_embedding,
                                )
                                stats["events_created"] += 1

                            stats["articles_processed"] += 1
                    except Exception:
                        logger.exception("failed to process article: %s.", article.title)
                        stats["articles_failed"] += 1

        logger.info(
            "finished source '%s': %s processed, %s skipped (duplicates), %s failed.",
            source_name,
            stats["articles_processed"],
            stats["articles_skipped"],
            stats["articles_failed"],
        )
        return stats




    async def _get_active_sources(self, session: AsyncSession, force: bool = False) -> list[dict]:
        stmt = (
            select(
                Source.id,
                Source.name,
                Source.feed_url,
                Source.last_fetched_at,
                Source.fetch_interval_minutes,
                Source.credibility,
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
                due_sources.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "feed_url": row.feed_url,
                        "credibility": row.credibility,
                    }
                )
                continue

            last = row.last_fetched_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)

            delta = timedelta(minutes=row.fetch_interval_minutes)
            if force or now >= last + delta:
                due_sources.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "feed_url": row.feed_url,
                        "credibility": row.credibility,
                    }
                )


        return due_sources




    async def ingest_all_sources(self, force: bool = False) -> dict[str, int]:
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
            sources = await self._get_active_sources(session, force=force)
        if not sources:
            logger.warning("no active sources found in the database.")
            return stats


        logger.info("starting ingestion for %s sources.", len(sources))
        semaphore = asyncio.Semaphore(5)
        async def _process_source(source: dict) -> dict[str, int]:
            async with semaphore:
                try:
                    s_stats = await self._ingest_source(source)
                    async with AsyncSessionLocal() as db_session:
                        await db_session.execute(
                            update(Source)
                            .where(Source.id == source["id"])
                            .values(last_fetched_at=func.now())
                        )
                        await db_session.commit()
                    return s_stats
                except Exception:
                    logger.exception("unhandled error ingesting source %s.", source["name"])
                    return { k: 0 for k in stats if k != "sources_processed" }


        tasks = [_process_source(s) for s in sources]
        results = await asyncio.gather(*tasks)
        for source_stats in results:
            for key in source_stats:
                if key in stats:
                    stats[key] += source_stats[key]
            stats["sources_processed"] += 1


        logger.info(
            "ingestion complete: %s sources, %s articles processed, %s new events, %s matched to existing.",
            stats["sources_processed"],
            stats["articles_processed"],
            stats["events_created"],
            stats["events_matched"],
        )
        return stats
