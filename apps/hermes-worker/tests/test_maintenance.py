"""Unit tests for the maintenance stages."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from hermes_db.services.event_lifecycle import LifecycleResult
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, LlmBudget, WorkerIdentity
from hermes_worker.jobs.stages.maintenance import (
    EventLifecycleStage,
    RequeueStaleClaimsStage,
    ThreadLifecycleStage,
)


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "EVENT_STALE_HOURS": 24,
        "EVENT_ARCHIVE_HOURS": 48,
        "ARTICLE_CLAIM_BATCH_SIZE": 50,
        "ARTICLE_CLAIM_STALE_MINUTES": 30,
        "ARTICLE_MAX_ATTEMPTS": 3,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _context(settings: Settings) -> tuple[JobContext, AsyncMock]:
    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    ctx = JobContext(
        settings=settings,
        engine=MagicMock(),
        session_factory=MagicMock(return_value=session_cm),
        identity=WorkerIdentity(hostname="host", pid=1),
        budget=LlmBudget(max_llm_calls=1),
    )
    return ctx, session


def test_requeue_stale_claims_stage_commits_and_counts() -> None:
    async def _test() -> None:
        ctx, session = _context(_settings())

        with patch("hermes_worker.jobs.stages.maintenance.ArticleQueue") as queue_cls:
            queue = queue_cls.return_value
            queue.requeue_stale = AsyncMock(return_value=(2, 1))

            stats = await RequeueStaleClaimsStage().run(ctx)

        queue_cls.assert_called_once_with(session)
        call = queue.requeue_stale.await_args
        assert call is not None
        assert call.kwargs["limit"] == 50
        assert call.kwargs["max_attempts"] == 3
        age = datetime.now(UTC) - call.kwargs["older_than"]
        assert timedelta(minutes=29) < age < timedelta(minutes=31)
        session.commit.assert_awaited_once()
        assert stats.counters == {"requeued": 2, "failed": 1}

    asyncio.run(_test())


def test_event_lifecycle_stage_commits_and_counts() -> None:
    async def _test() -> None:
        ctx, session = _context(_settings())

        with patch(
            "hermes_worker.jobs.stages.maintenance.EventLifecycleService"
        ) as service_cls:
            service = service_cls.return_value
            service.run = AsyncMock(return_value=LifecycleResult(staled=4, archived=2))

            stats = await EventLifecycleStage().run(ctx)

        service_cls.assert_called_once_with(session)
        service.run.assert_awaited_once_with(
            stale_hours=24,
            archive_hours=48,
        )
        session.commit.assert_awaited_once()
        assert stats.counters == {"staled": 4, "archived": 2}

    asyncio.run(_test())


def test_event_lifecycle_stage_does_not_commit_on_failure() -> None:
    async def _test() -> None:
        ctx, session = _context(_settings())

        with patch(
            "hermes_worker.jobs.stages.maintenance.EventLifecycleService"
        ) as service_cls:
            service = service_cls.return_value
            service.run = AsyncMock(side_effect=RuntimeError("database unavailable"))

            with pytest.raises(RuntimeError, match="database unavailable"):
                await EventLifecycleStage().run(ctx)

        session.commit.assert_not_awaited()

    asyncio.run(_test())


def test_thread_lifecycle_stage_commits_and_counts() -> None:
    async def _test() -> None:
        ctx, session = _context(_settings())

        with patch(
            "hermes_worker.jobs.stages.maintenance.ThreadService"
        ) as service_cls:
            service = service_cls.return_value
            service.run_lifecycle = AsyncMock(return_value={"dormant": 3, "ended": 1})

            stats = await ThreadLifecycleStage().run(ctx)

        service_cls.assert_called_once_with(session)
        service.run_lifecycle.assert_awaited_once_with()
        session.commit.assert_awaited_once()
        assert stats.counters == {"dormant": 3, "ended": 1}

    asyncio.run(_test())
