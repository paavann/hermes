from __future__ import annotations
import asyncio
import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from hermes_ai.utils.sanitization import strip_html_text
from hermes_db.enums import SourceType
from hermes_db.services import (
    ArticleLedgerRow,
    ArticleService,
    DueSource,
    SourceService,
    sync_sources_from_config,
)
from hermes_db.utils.datetime import ensure_utc
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, StageName, StageStats
from hermes_worker.jobs.urls import canonical_url_hash, canonicalize_url
from hermes_worker.services.fetchers import (
    BaseArticleFetcher,
    GDELTFetcher,
    ParsedArticle,
    RSSFetcher,
    SitemapFetcher,
)


logger = logging.getLogger(__name__)

MAX_SUMMARY_CHARS: int = 4000


def build_fetchers(settings: Settings) -> dict[SourceType, BaseArticleFetcher]:
    """Build one fetcher per supported source type for a single run."""
    return {
        SourceType.RSS: RSSFetcher(user_agent=settings.ARTICLE_FETCH_USER_AGENT),
        SourceType.GDELT: GDELTFetcher(settings=settings),
        SourceType.SCRAPE: SitemapFetcher(settings=settings),
    }


def _is_redundant_summary(title: str, summary: str) -> bool:
    norm_title = " ".join(title.lower().split())
    norm_summary = " ".join(summary.lower().split())
    if not norm_summary:
        return True
    if norm_summary == norm_title:
        return True
    if norm_summary.startswith(norm_title):
        remainder = norm_summary.removeprefix(norm_title).lstrip(" -–—|·•")
        if len(remainder) <= 45 and len(remainder.split()) <= 5:
            return True
    return False


def _select_feed_summary(
    title: str,
    description: str,
    content: str | None,
) -> str | None:
    clean_desc = strip_html_text(description, limit=MAX_SUMMARY_CHARS)
    clean_content = (
        strip_html_text(content, limit=MAX_SUMMARY_CHARS) if content else ""
    )
    if _is_redundant_summary(title, clean_desc):
        if clean_content and not _is_redundant_summary(title, clean_content):
            return clean_content
        return None
    if clean_content and len(clean_content) > len(clean_desc):
        return clean_content
    return clean_desc or None


def normalize_published_at(
    published_at: datetime | None,
    *,
    now: datetime,
    max_age: timedelta,
    future_skew: timedelta,
) -> tuple[datetime | None, bool]:
    """Apply the freshness window.

    Returns the value to store and whether the entry is too old to keep.
    Future timestamps within the skew window are clamped to ``now`` so a
    publisher clock error cannot pin an article above newer events.
    """
    if published_at is None:
        return None, False

    value = ensure_utc(published_at)
    if value < now - max_age:
        return None, True
    if value > now + future_skew:
        return now, False
    return value, False


def prepare_rows(
    source: DueSource,
    articles: Sequence[ParsedArticle],
    *,
    now: datetime,
    max_age: timedelta,
    future_skew: timedelta,
) -> tuple[list[ArticleLedgerRow], int, int]:
    """Convert fetched entries into ledger rows.

    Returns ``(rows, stale, invalid)``. Repeated canonical URLs inside one
    feed are collapsed before the insert so the conflict count reflects only
    rows that already existed in the database.
    """
    rows: list[ArticleLedgerRow] = []
    seen: set[str] = set()
    stale = 0
    invalid = 0

    for article in articles:
        title = " ".join(article.title.split())
        canonical = canonicalize_url(article.url)
        if not title or canonical is None:
            invalid += 1
            continue

        published_at, too_old = normalize_published_at(
            article.published_at,
            now=now,
            max_age=max_age,
            future_skew=future_skew,
        )
        if too_old:
            stale += 1
            continue

        digest = canonical_url_hash(canonical)
        if digest in seen:
            continue
        seen.add(digest)

        summary = _select_feed_summary(title, article.description, article.content)

        rows.append(
            {
                "source_id": source.id,
                "title": title,
                "url": article.url,
                "canonical_url": canonical,
                "canonical_url_hash": digest,
                "feed_summary": summary,
                "published_at": published_at,
                "language": source.language,
            }
        )

    return rows, stale, invalid


class IngestStage:
    """Fetch due sources and write the deduplicated article ledger."""

    name = StageName.INGEST

    def __init__(
        self,
        *,
        force: bool = False,
        fetchers: Mapping[SourceType, BaseArticleFetcher] | None = None,
    ) -> None:
        self._force = force
        self._fetchers = fetchers

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()

        async with ctx.session_factory() as session:
            sync_stats = await sync_sources_from_config(session)
            await session.commit()
        stats.add("sources_inserted", sync_stats["inserted"])
        stats.add("sources_updated", sync_stats["updated"])
        stats.add("sources_disabled", sync_stats["disabled"])

        async with ctx.session_factory() as session:
            sources = await SourceService(session).get_due_sources(force=self._force)
        stats.add("sources_due", len(sources))
        if not sources:
            return stats

        fetchers = (
            dict(self._fetchers)
            if self._fetchers is not None
            else build_fetchers(ctx.settings)
        )
        semaphore = asyncio.Semaphore(ctx.settings.SOURCE_FETCH_CONCURRENCY)
        now = datetime.now(UTC)
        max_age = timedelta(hours=ctx.settings.ARTICLE_MAX_AGE_HOURS)
        future_skew = timedelta(hours=ctx.settings.ARTICLE_FUTURE_SKEW_HOURS)

        async def run_source(source: DueSource) -> dict[str, int]:
            async with semaphore:
                return await self._ingest_source(
                    ctx,
                    source,
                    fetchers,
                    now=now,
                    max_age=max_age,
                    future_skew=future_skew,
                )

        results = await asyncio.gather(*(run_source(source) for source in sources))
        for counters in results:
            for name, value in counters.items():
                stats.add(name, value)

        return stats

    async def _ingest_source(
        self,
        ctx: JobContext,
        source: DueSource,
        fetchers: Mapping[SourceType, BaseArticleFetcher],
        *,
        now: datetime,
        max_age: timedelta,
        future_skew: timedelta,
    ) -> dict[str, int]:
        counters = {
            "fetched": 0,
            "entries": 0,
            "inserted": 0,
            "duplicates": 0,
            "stale": 0,
            "invalid": 0,
            "errors": 0,
        }

        fetcher = fetchers.get(source.source_type)
        if fetcher is None:
            message = f"no fetcher for source type {source.source_type.value}"
            logger.warning("skipping source '%s': %s.", source.name, message)
            counters["errors"] += 1
            await self._record_health(ctx, source, error=message)
            return counters

        try:
            articles = await fetcher.fetch_articles(source)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            logger.warning("failed to fetch source '%s': %s.", source.name, message)
            counters["errors"] += 1
            await self._record_health(ctx, source, error=message)
            return counters

        counters["fetched"] = 1
        counters["entries"] = len(articles)
        rows, stale, invalid = prepare_rows(
            source,
            articles,
            now=now,
            max_age=max_age,
            future_skew=future_skew,
        )
        counters["stale"] = stale
        counters["invalid"] = invalid

        inserted = 0
        if rows:
            try:
                async with ctx.session_factory() as session:
                    inserted = await ArticleService(session).insert_ledger_rows(rows)
                    await session.commit()
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "failed to store articles for source '%s': %s.",
                    source.name,
                    message,
                )
                counters["errors"] += 1
                await self._record_health(ctx, source, error=message)
                return counters

        counters["inserted"] = inserted
        counters["duplicates"] = len(rows) - inserted
        await self._record_health(ctx, source, error=None)
        return counters

    async def _record_health(
        self,
        ctx: JobContext,
        source: DueSource,
        *,
        error: str | None,
    ) -> None:
        try:
            async with ctx.session_factory() as session:
                service = SourceService(session)
                if error is None:
                    await service.record_fetch_success(source.id)
                else:
                    await service.record_fetch_failure(source.id, error)
                await session.commit()
        except Exception as exc:
            logger.warning(
                "failed to record fetch health for source '%s': %s.",
                source.name,
                exc,
            )
