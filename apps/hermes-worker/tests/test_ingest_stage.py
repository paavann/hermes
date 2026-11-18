import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from hermes_db.enums import CredibilityTier, SourceType
from hermes_db.services import DueSource
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, LlmBudget, WorkerIdentity
from hermes_worker.jobs.stages.ingest import (
    IngestStage,
    normalize_published_at,
    prepare_rows,
)
from hermes_worker.services.fetchers.base import ParsedArticle


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "ARTICLE_MAX_AGE_HOURS": 72,
        "ARTICLE_FUTURE_SKEW_HOURS": 2,
        "SOURCE_FETCH_CONCURRENCY": 1,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _source(**overrides: object) -> DueSource:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": "Test Source",
        "feed_url": "https://example.com/rss",
        "credibility": CredibilityTier.TIER_1,
        "source_type": SourceType.RSS,
        "language": "en",
    }
    values.update(overrides)
    return DueSource(**values)


def _context(settings: Settings) -> tuple[JobContext, list[AsyncMock]]:
    sessions: list[AsyncMock] = []

    def factory() -> AsyncMock:
        session = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=session)
        cm.__aexit__ = AsyncMock(return_value=False)
        sessions.append(session)
        return cm

    ctx = JobContext(
        settings=settings,
        engine=MagicMock(),
        session_factory=factory,
        identity=WorkerIdentity(hostname="host", pid=1),
        budget=LlmBudget(max_llm_calls=1),
    )
    return ctx, sessions


class _Fetcher:
    def __init__(
        self,
        articles: list[ParsedArticle] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._articles = articles or []
        self._error = error
        self.calls = 0

    async def fetch_articles(self, source: DueSource) -> list[ParsedArticle]:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._articles


def _article(**overrides: object) -> ParsedArticle:
    values: dict[str, object] = {
        "title": "Flooding hits coastal city",
        "url": "https://example.com/world/flooding",
        "description": "Hundreds evacuate after heavy rain.",
        "published_at": datetime.now(UTC) - timedelta(hours=1),
    }
    values.update(overrides)
    return ParsedArticle(**values)


async def _run_stage(
    stage: IngestStage,
    ctx: JobContext,
    *,
    due: list[DueSource],
    insert_count: int | list[int] = 1,
    sync_stats: dict[str, int] | None = None,
    fetch_success: AsyncMock | None = None,
    fetch_failure: AsyncMock | None = None,
) -> tuple[dict[str, int], MagicMock, MagicMock]:
    service = MagicMock()
    service.get_due_sources = AsyncMock(return_value=due)
    service.record_fetch_success = fetch_success or AsyncMock()
    service.record_fetch_failure = fetch_failure or AsyncMock()

    article_service = MagicMock()
    article_service.insert_ledger_rows = AsyncMock(
        side_effect=insert_count if isinstance(insert_count, list) else None,
        return_value=None if isinstance(insert_count, list) else insert_count,
    )

    with (
        patch(
            "hermes_worker.jobs.stages.ingest.sync_sources_from_config",
            new_callable=AsyncMock,
            return_value=sync_stats or {"inserted": 0, "updated": 0, "disabled": 0},
        ),
        patch(
            "hermes_worker.jobs.stages.ingest.SourceService",
            return_value=service,
        ) as service_cls,
        patch(
            "hermes_worker.jobs.stages.ingest.ArticleService",
            return_value=article_service,
        ) as article_cls,
    ):
        stats = await stage.run(ctx)

    return stats.counters, service_cls, article_cls


def test_ingest_stage_inserts_fresh_rows_and_records_health() -> None:
    async def _test() -> None:
        ctx, sessions = _context(_settings())
        source = _source()
        fetcher = _Fetcher([_article()])
        fetch_success = AsyncMock()

        counters, _, article_cls = await _run_stage(
            IngestStage(fetchers={SourceType.RSS: fetcher}),
            ctx,
            due=[source],
            fetch_success=fetch_success,
        )

        assert counters == {
            "sources_inserted": 0,
            "sources_updated": 0,
            "sources_disabled": 0,
            "sources_due": 1,
            "fetched": 1,
            "entries": 1,
            "inserted": 1,
            "duplicates": 0,
            "stale": 0,
            "invalid": 0,
            "errors": 0,
        }
        assert fetcher.calls == 1
        article_cls.assert_called_once()
        rows = article_cls.return_value.insert_ledger_rows.await_args.args[0]
        assert rows[0]["source_id"] == source.id
        assert rows[0]["canonical_url"] == "https://example.com/world/flooding"
        assert rows[0]["canonical_url_hash"] is not None
        assert rows[0]["language"] == "en"
        fetch_success.assert_awaited_once()
        sessions[0].commit.assert_awaited_once()

    asyncio.run(_test())


def test_ingest_stage_counts_duplicates_on_repeat_run() -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())
        source = _source()
        fetcher = _Fetcher([_article()])
        stage = IngestStage(fetchers={SourceType.RSS: fetcher})

        first, _, _ = await _run_stage(stage, ctx, due=[source], insert_count=1)
        second, _, _ = await _run_stage(stage, ctx, due=[source], insert_count=0)

        assert first["inserted"] == 1
        assert first["duplicates"] == 0
        assert second["inserted"] == 0
        assert second["duplicates"] == 1
        assert fetcher.calls == 2

    asyncio.run(_test())


def test_ingest_stage_skips_stale_entries_before_insert() -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())
        stale = _article(published_at=datetime.now(UTC) - timedelta(hours=100))
        fetcher = _Fetcher([stale])

        counters, _, article_cls = await _run_stage(
            IngestStage(fetchers={SourceType.RSS: fetcher}),
            ctx,
            due=[_source()],
        )

        assert counters["stale"] == 1
        assert counters["inserted"] == 0
        article_cls.return_value.insert_ledger_rows.assert_not_awaited()

    asyncio.run(_test())


def test_ingest_stage_skips_invalid_entries_before_insert() -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())
        fetcher = _Fetcher(
            [
                _article(title="   "),
                _article(url="ftp://example.com/file"),
            ]
        )

        counters, _, article_cls = await _run_stage(
            IngestStage(fetchers={SourceType.RSS: fetcher}),
            ctx,
            due=[_source()],
        )

        assert counters["invalid"] == 2
        assert counters["inserted"] == 0
        article_cls.return_value.insert_ledger_rows.assert_not_awaited()

    asyncio.run(_test())


def test_ingest_stage_collapses_duplicate_urls_within_one_feed() -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())
        fetcher = _Fetcher(
            [
                _article(url="https://example.com/story?utm_source=rss"),
                _article(url="https://example.com/story"),
            ]
        )

        counters, _, article_cls = await _run_stage(
            IngestStage(fetchers={SourceType.RSS: fetcher}),
            ctx,
            due=[_source()],
        )

        rows = article_cls.return_value.insert_ledger_rows.await_args.args[0]
        assert len(rows) == 1
        assert counters["entries"] == 2
        assert counters["duplicates"] == 0

    asyncio.run(_test())


def test_ingest_stage_records_fetch_failure() -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())
        fetcher = _Fetcher(error=RuntimeError("feed exploded"))
        fetch_failure = AsyncMock()

        counters, _, article_cls = await _run_stage(
            IngestStage(fetchers={SourceType.RSS: fetcher}),
            ctx,
            due=[_source()],
            fetch_failure=fetch_failure,
        )

        assert counters["errors"] == 1
        assert counters["fetched"] == 0
        fetch_failure.assert_awaited_once()
        assert "RuntimeError: feed exploded" in fetch_failure.await_args.args[1]
        article_cls.return_value.insert_ledger_rows.assert_not_awaited()

    asyncio.run(_test())


def test_ingest_stage_records_missing_fetcher() -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())
        fetch_failure = AsyncMock()

        counters, _, _ = await _run_stage(
            IngestStage(fetchers={}),
            ctx,
            due=[_source()],
            fetch_failure=fetch_failure,
        )

        assert counters["errors"] == 1
        fetch_failure.assert_awaited_once()

    asyncio.run(_test())


def test_ingest_stage_returns_early_when_no_sources_are_due() -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())
        fetcher = _Fetcher([_article()])

        counters, _, _ = await _run_stage(
            IngestStage(fetchers={SourceType.RSS: fetcher}),
            ctx,
            due=[],
        )

        assert counters["sources_due"] == 0
        assert fetcher.calls == 0

    asyncio.run(_test())


def test_ingest_stage_counts_source_sync() -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())

        counters, _, _ = await _run_stage(
            IngestStage(fetchers={}),
            ctx,
            due=[],
            sync_stats={"inserted": 2, "updated": 1, "disabled": 3},
        )

        assert counters["sources_inserted"] == 2
        assert counters["sources_updated"] == 1
        assert counters["sources_disabled"] == 3

    asyncio.run(_test())


def test_prepare_rows_clamps_future_timestamps() -> None:
    now = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
    source = _source()

    rows, stale, invalid = prepare_rows(
        source,
        [_article(published_at=now + timedelta(hours=10))],
        now=now,
        max_age=timedelta(hours=72),
        future_skew=timedelta(hours=2),
    )

    assert stale == 0
    assert invalid == 0
    assert rows[0]["published_at"] == now


def test_prepare_rows_preserves_missing_published_time() -> None:
    now = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)

    rows, stale, invalid = prepare_rows(
        _source(),
        [_article(published_at=None)],
        now=now,
        max_age=timedelta(hours=72),
        future_skew=timedelta(hours=2),
    )

    assert (stale, invalid) == (0, 0)
    assert rows[0]["published_at"] is None


def test_normalize_published_at_boundaries() -> None:
    now = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
    max_age = timedelta(hours=72)
    future_skew = timedelta(hours=2)

    at_cutoff, stale = normalize_published_at(
        now - max_age,
        now=now,
        max_age=max_age,
        future_skew=future_skew,
    )
    assert at_cutoff == now - max_age
    assert stale is False

    just_stale, stale = normalize_published_at(
        now - max_age - timedelta(seconds=1),
        now=now,
        max_age=max_age,
        future_skew=future_skew,
    )
    assert just_stale is None
    assert stale is True

    within_skew, stale = normalize_published_at(
        now + future_skew,
        now=now,
        max_age=max_age,
        future_skew=future_skew,
    )
    assert within_skew == now + future_skew
    assert stale is False


@pytest.mark.parametrize("insert_count", [0, 1, 2])
def test_ingest_stage_insert_count_drives_duplicate_counter(
    insert_count: int,
) -> None:
    async def _test() -> None:
        ctx, _ = _context(_settings())
        fetcher = _Fetcher(
            [
                _article(url="https://example.com/a"),
                _article(url="https://example.com/b"),
                _article(url="https://example.com/c"),
            ]
        )

        counters, _, _ = await _run_stage(
            IngestStage(fetchers={SourceType.RSS: fetcher}),
            ctx,
            due=[_source()],
            insert_count=insert_count,
        )

        assert counters["inserted"] == insert_count
        assert counters["duplicates"] == 3 - insert_count

    asyncio.run(_test())
