import asyncio
import logging
import uuid
from hermes_ai import (
    ARTICLE_BATCH_SIZE,
    ArticleInput,
    GeocodingService,
)
from hermes_db.services import (
    DueSource,
    EventService,
    GeocodeCacheService,
    SourceService,
)
from hermes_db.session import AsyncSessionLocal
from hermes_worker.services.ai import AiService
from hermes_worker.services.rss import ParsedArticle, fetch_feed


logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self) -> None:
        self._ai = AiService()


    async def _sync_source(self, source: DueSource) -> dict[str, int]:
        stats = {
            "articles_fetched": 0,
            "articles_skipped": 0,
            "articles_processed": 0,
            "articles_failed": 0,
            "events_created": 0,
            "events_matched": 0,
        }
        feed_url = source.feed_url
        source_id = source.id
        source_name = source.name

        logger.info("syncing source: %s (%s).", source_name, feed_url)
        articles = await fetch_feed(feed_url)
        stats["articles_fetched"] = len(articles)
        if not articles:
            logger.info("no articles found in %s.", source_name)
            return stats

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

        for batch_start in range(0, len(articles_to_process), ARTICLE_BATCH_SIZE):
            batch = articles_to_process[batch_start : batch_start + ARTICLE_BATCH_SIZE]
            ai_inputs = [
                ArticleInput(title=a.title, content=a.text_for_ai) for a in batch
            ]
            batch_texts = [f"{a.title}\n{a.text_for_ai}" for a in batch]
            embeddings = await self._ai.gen_embeddings(batch_texts)
            async with AsyncSessionLocal() as session:
                event_service = EventService(session)
                existing_events = await event_service.get_active_events_by_embeddings(
                    embeddings
                )

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
                            geocoding_svc = GeocodingService(
                                GeocodeCacheService(session)
                            )
                            geocoding = await geocoding_svc.geocode(
                                extraction.location_name
                            )

                        matched = False
                        if extraction.matched_event_id:
                            try:
                                matched_uuid = uuid.UUID(extraction.matched_event_id)
                            except ValueError:
                                logger.warning(
                                    "ignoring malformed matched_event_id '%s' for article '%s'.",
                                    extraction.matched_event_id,
                                    article.title,
                                )
                                matched_uuid = None

                            if matched_uuid:
                                matched = await event_service.add_article_to_event(
                                    event_id=matched_uuid,
                                    article_title=article.title,
                                    article_url=article.url,
                                    source_id=source_id,
                                    source_credibility=source.credibility,
                                    published_at=article.published_at,
                                )
                                if matched:
                                    stats["events_matched"] += 1

                        if not matched:
                            created = await event_service.create_event_with_article(
                                extraction=extraction,
                                geocoding=geocoding,
                                article_title=article.title,
                                article_url=article.url,
                                source_id=source_id,
                                source_credibility=source.credibility,
                                published_at=article.published_at,
                                embedding=article_embedding,
                            )
                            if created:
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


    async def sync_all_sources(self, force: bool = False) -> dict[str, int]:
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
            source_service = SourceService(session)
            sources = await source_service.get_due_sources(force=force)
        if not sources:
            logger.warning("no active sources found due for sync.")
            return stats

        logger.info("starting sync for %s sources.", len(sources))
        semaphore = asyncio.Semaphore(5)

        async def _process_source(source: DueSource) -> dict[str, int]:
            async with semaphore:
                try:
                    s_stats = await self._sync_source(source)
                    async with AsyncSessionLocal() as db_session:
                        source_service = SourceService(db_session)
                        await source_service.update_last_fetched(source.id)
                        await db_session.commit()
                    return s_stats
                except Exception:
                    logger.exception("unhandled error syncing source %s.", source.name)
                    return {k: 0 for k in stats if k != "sources_processed"}

        tasks = [_process_source(s) for s in sources]
        results = await asyncio.gather(*tasks)
        for source_stats in results:
            for key in source_stats:
                if key in stats:
                    stats[key] += source_stats[key]
            stats["sources_processed"] += 1

        logger.info(
            "sync complete: %s sources, %s articles processed, %s new events, %s matched to existing.",
            stats["sources_processed"],
            stats["articles_processed"],
            stats["events_created"],
            stats["events_matched"],
        )
        return stats
