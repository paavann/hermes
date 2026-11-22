"""Tests for the score stage pagination and counters."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, LlmBudget, WorkerIdentity
from hermes_worker.jobs.stages.score import ScoreStage


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "EVENT_SCORE_PAGE_SIZE": 2,
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
        budget=LlmBudget(max_llm_calls=10),
    )
    return ctx, session


def _state() -> MagicMock:
    state = MagicMock()
    state.id = uuid.uuid4()
    return state


def test_score_stage_pages_until_short_page() -> None:
    async def _test() -> None:
        ctx, session = _context(_settings())
        first_page = [_state(), _state()]
        second_page = [_state()]

        with patch(
            "hermes_worker.jobs.stages.score.EventScoringService"
        ) as service_cls:
            service = service_cls.return_value
            service.active_states = AsyncMock(side_effect=[first_page, second_page])
            service.rescore = AsyncMock(
                return_value=MagicMock(capped=False, breaking_override=False)
            )

            stats = await ScoreStage().run(ctx)

        assert stats.counters["scored"] == 3
        assert service.active_states.await_count == 2
        assert service.rescore.await_count == 3
        assert session.commit.await_count == 2

        first_call, second_call = service.active_states.await_args_list
        assert first_call.kwargs["after_id"] is None
        assert second_call.kwargs["after_id"] == first_page[-1].id

    asyncio.run(_test())


def test_score_stage_counts_capped_and_breaking() -> None:
    async def _test() -> None:
        ctx, _session = _context(_settings(EVENT_SCORE_PAGE_SIZE=10))

        with patch(
            "hermes_worker.jobs.stages.score.EventScoringService"
        ) as service_cls:
            service = service_cls.return_value
            service.active_states = AsyncMock(return_value=[_state()])
            service.rescore = AsyncMock(
                return_value=MagicMock(capped=True, breaking_override=True)
            )

            stats = await ScoreStage().run(ctx)

        assert stats.counters == {
            "scored": 1,
            "capped_single_source": 1,
            "breaking": 1,
        }

    asyncio.run(_test())


def test_score_stage_counts_missing_events() -> None:
    async def _test() -> None:
        ctx, _session = _context(_settings(EVENT_SCORE_PAGE_SIZE=10))

        with patch(
            "hermes_worker.jobs.stages.score.EventScoringService"
        ) as service_cls:
            service = service_cls.return_value
            service.active_states = AsyncMock(return_value=[_state()])
            service.rescore = AsyncMock(return_value=None)

            stats = await ScoreStage().run(ctx)

        assert stats.counters == {"missing": 1}

    asyncio.run(_test())


def test_score_stage_with_no_events_is_idempotent() -> None:
    async def _test() -> None:
        ctx, session = _context(_settings())

        with patch(
            "hermes_worker.jobs.stages.score.EventScoringService"
        ) as service_cls:
            service = service_cls.return_value
            service.active_states = AsyncMock(return_value=[])
            service.rescore = AsyncMock()

            first = await ScoreStage().run(ctx)
            second = await ScoreStage().run(ctx)

        assert first.counters == {}
        assert second.counters == {}
        assert service.rescore.await_count == 0
        assert session.commit.await_count == 2

    asyncio.run(_test())
