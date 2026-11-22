"""Tests for thread grouping helpers and the thread stage assignment flow."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from hermes_db.enums import ThreadKind, ThreadStatus
from hermes_db.services import ThreadCandidate, ThreadEventSnapshot, ThreadMatch
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, LlmBudget, WorkerIdentity
from hermes_worker.jobs.stages.thread import (
    ThreadStage,
    _centroid,
    _event_side,
    _group_entities,
    _group_key,
    _pair_hash,
    _thread_side,
)


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "THREAD_EVENT_LIMIT": 100,
        "THREAD_CANDIDATE_LIMIT": 40,
        "THREAD_MIN_GROUP": 2,
        "THREAD_LLM_PAIRS_PER_RUN": 20,
        "THREAD_ADJUDICATION_BATCH_SIZE": 10,
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


def _snapshot(
    *,
    event_id: uuid.UUID | None = None,
    category: str = "CONFLICT",
    entities: frozenset[str] = frozenset({"kyiv"}),
    embedding: tuple[float, ...] | None = None,
    embedding_model: str | None = None,
    importance: float = 70.0,
    published_at: datetime = NOW,
) -> ThreadEventSnapshot:
    return ThreadEventSnapshot(
        id=event_id or uuid.uuid4(),
        ai_headline="Explosion hits market",
        ai_summary="An explosion struck the central market.",
        category=category,
        event_time=published_at,
        latest_published_at=published_at,
        first_reported_at=published_at,
        importance_score=importance,
        latitude=50.45,
        longitude=30.52,
        embedding=embedding,
        embedding_model=embedding_model,
        facts=("An explosion struck the central market.",),
        entities=entities,
        locations=("Kyiv",),
    )


def _match(*, score: float) -> ThreadMatch:
    candidate = ThreadCandidate(
        id=uuid.uuid4(),
        name="Kyiv strikes",
        description="Tracking strikes on Kyiv.",
        kind=ThreadKind.DEVELOPING,
        status=ThreadStatus.ACTIVE,
        last_event_at=NOW,
        importance=60.0,
        event_count=3,
        embedding=None,
        embedding_model=None,
        entities=frozenset({"kyiv"}),
    )
    return ThreadMatch(
        candidate=candidate,
        score=score,
        embedding_similarity=score,
        entity_similarity=1.0,
    )


class TestGroupKey:
    def test_uses_category_and_sorted_entities(self) -> None:
        event = _snapshot(entities=frozenset({"mayor", "kyiv"}))

        assert _group_key(event) == ("CONFLICT", "kyiv", "mayor")

    def test_uses_single_entity(self) -> None:
        event = _snapshot(entities=frozenset({"kyiv"}))

        assert _group_key(event) == ("CONFLICT", "kyiv")

    def test_returns_none_without_entities(self) -> None:
        assert _group_key(_snapshot(entities=frozenset())) is None


class TestGroupEntities:
    def test_keeps_only_entities_shared_by_two_events(self) -> None:
        first = _snapshot(entities=frozenset({"kyiv", "mayor", "army"}))
        second = _snapshot(entities=frozenset({"kyiv", "mayor"}))
        third = _snapshot(entities=frozenset({"kyiv"}))

        entities = _group_entities([first, second, third])

        assert entities == ["kyiv", "mayor"]

    def test_orders_by_shared_count_then_name(self) -> None:
        first = _snapshot(entities=frozenset({"alpha", "beta"}))
        second = _snapshot(entities=frozenset({"alpha", "beta"}))

        assert _group_entities([first, second]) == ["alpha", "beta"]


class TestCentroid:
    def test_averages_vectors_from_same_model(self) -> None:
        first = _snapshot(embedding=(1.0, 0.0), embedding_model="m")
        second = _snapshot(embedding=(0.0, 1.0), embedding_model="m")

        centroid, model = _centroid([first, second])

        assert centroid == [0.5, 0.5]
        assert model == "m"

    def test_returns_none_without_embeddings(self) -> None:
        assert _centroid([_snapshot()]) == (None, None)


class TestPairHash:
    def test_changes_with_thread_last_event_at(self) -> None:
        import dataclasses

        event = _snapshot()
        match = _match(score=0.8)
        other = _match(score=0.8)
        other = dataclasses.replace(
            other,
            candidate=dataclasses.replace(
                other.candidate,
                last_event_at=NOW + timedelta(hours=1),
            ),
        )

        assert _pair_hash(event.id, match, "v1") != _pair_hash(event.id, other, "v1")

    def test_changes_with_prompt_version(self) -> None:
        event = _snapshot()
        match = _match(score=0.8)

        assert _pair_hash(event.id, match, "v1") != _pair_hash(event.id, match, "v2")


class TestSides:
    def test_event_side_includes_entities_and_location(self) -> None:
        side = _event_side(_snapshot(entities=frozenset({"kyiv", "mayor"})))

        assert side.entities == ["kyiv", "mayor"]
        assert side.location == "Kyiv"

    def test_thread_side_includes_metadata(self) -> None:
        side = _thread_side(_match(score=0.9))

        assert side.name == "Kyiv strikes"
        assert side.event_count == 3
        assert side.entities == ["kyiv"]


class TestThreadRun:
    def test_returns_early_without_unthreaded_events(self) -> None:
        async def _test() -> None:
            ctx, _session = _context(_settings())

            with patch("hermes_worker.jobs.stages.thread.ThreadService") as service_cls:
                service_cls.return_value.unthreaded_events = AsyncMock(return_value=[])

                stats = await ThreadStage().run(ctx)

            assert stats.counters == {"unthreaded": 0}

        asyncio.run(_test())

    def test_auto_assigns_high_confidence_match(self) -> None:
        async def _test() -> None:
            ctx, _session = _context(_settings())
            event = _snapshot()
            match = _match(score=0.90)

            with patch("hermes_worker.jobs.stages.thread.ThreadService") as service_cls:
                service = service_cls.return_value
                service.unthreaded_events = AsyncMock(return_value=[event])
                service.ranked_candidates = AsyncMock(return_value=[match])
                service.assign_event = AsyncMock(return_value=True)

                stats = await ThreadStage().run(ctx)

            assert stats.counters["assigned_auto"] == 1
            service.assign_event.assert_awaited_once()
            assert service.assign_event.await_args.args[0] == event.id
            assert service.assign_event.await_args.args[1] == match.candidate.id

        asyncio.run(_test())

    def test_groups_unmatched_events_into_new_thread(self) -> None:
        async def _test() -> None:
            ctx, _session = _context(_settings())
            first = _snapshot(importance=80.0)
            second = _snapshot(importance=60.0)
            thread = MagicMock()
            thread.id = uuid.uuid4()
            thread.kind = ThreadKind.DEVELOPING

            with patch("hermes_worker.jobs.stages.thread.ThreadService") as service_cls:
                service = service_cls.return_value
                service.unthreaded_events = AsyncMock(return_value=[first, second])
                service.ranked_candidates = AsyncMock(return_value=[])
                service.create_thread = AsyncMock(return_value=thread)
                service.assign_event = AsyncMock(return_value=True)

                stats = await ThreadStage().run(ctx)

            assert stats.counters["threads_created"] == 1
            assert stats.counters["events_grouped"] == 2
            assert service.assign_event.await_count == 2
            created_name = service.create_thread.await_args.args[0]
            assert created_name.startswith("Kyiv — ")

        asyncio.run(_test())

    def test_unmatched_events_without_shared_entities_are_not_grouped(self) -> None:
        async def _test() -> None:
            ctx, _session = _context(_settings())
            first = _snapshot(entities=frozenset({"kyiv"}))
            second = _snapshot(entities=frozenset({"odesa"}))

            with patch("hermes_worker.jobs.stages.thread.ThreadService") as service_cls:
                service = service_cls.return_value
                service.unthreaded_events = AsyncMock(return_value=[first, second])
                service.ranked_candidates = AsyncMock(return_value=[])
                service.create_thread = AsyncMock()

                stats = await ThreadStage().run(ctx)

            assert stats.counters["unmatched"] == 2
            assert stats.counters.get("threads_created") is None
            service.create_thread.assert_not_awaited()

        asyncio.run(_test())
