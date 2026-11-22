"""Tests for reconcile merge selection, survivor choice, and budget handling."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from hermes_db.enums import EventStatus
from hermes_db.services import EventPairState
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, LlmBudget, WorkerIdentity
from hermes_worker.jobs.stages.reconcile import (
    ReconcileStage,
    _candidate_pairs,
    _event_side,
    _pair_hash,
    _survivor,
)


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "EVENT_RECONCILE_LIMIT": 200,
        "EVENT_RECONCILE_WINDOW_HOURS": 72,
        "EVENT_MERGE_LLM_PAIRS_PER_RUN": 25,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _context(
    settings: Settings,
    *,
    budget: int = 10,
    ai: object | None = None,
) -> tuple[JobContext, AsyncMock]:
    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    ctx = JobContext(
        settings=settings,
        engine=MagicMock(),
        session_factory=MagicMock(return_value=session_cm),
        identity=WorkerIdentity(hostname="host", pid=1),
        budget=LlmBudget(max_llm_calls=budget),
        ai=ai,  # type: ignore[arg-type]
    )
    return ctx, session


def _state(
    *,
    article_count: int = 2,
    first_reported_at: datetime = NOW,
    country_code: str | None = "UA",
    latitude: float | None = 50.45,
    longitude: float | None = 30.52,
    location_name: str | None = "Kyiv",
    event_time: datetime = NOW,
    embedding: tuple[float, ...] | None = None,
    category: str = "CONFLICT",
) -> EventPairState:
    return EventPairState(
        id=uuid.uuid4(),
        ai_headline="Explosion hits market",
        ai_summary="An explosion struck the central market.",
        category=category,
        event_time=event_time,
        latest_published_at=event_time,
        first_reported_at=first_reported_at,
        country_code=country_code,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        embedding=embedding,
        embedding_model="test-embed" if embedding is not None else None,
        member_hash="hash",
        article_count=article_count,
        thread_id=None,
        status=EventStatus.ACTIVE,
    )


class TestCandidatePairs:
    def test_keeps_duplicate_pairs_sorted_by_score(self) -> None:
        embedding = tuple([0.5] * 8)
        first = _state(embedding=embedding)
        second = _state(embedding=embedding)
        third = _state(embedding=(0.9, 0.1) * 4)

        pairs = _candidate_pairs(
            [first, second, third],
            families={},
            entities={
                first.id: {"kyiv"},
                second.id: {"kyiv"},
                third.id: {"kyiv"},
            },
        )

        assert len(pairs) >= 1
        scores = [pair.score.score for pair in pairs]
        assert scores == sorted(scores, reverse=True)

    def test_drops_pairs_below_gray_threshold(self) -> None:
        left = _state(embedding=(1.0, 0.0) * 4)
        right = _state(
            embedding=(0.0, 1.0) * 4,
            category="POLITICS",
            location_name="Lviv",
            latitude=49.84,
            longitude=24.03,
        )

        pairs = _candidate_pairs(
            [left, right],
            families={},
            entities={left.id: {"kyiv"}, right.id: {"kyiv"}},
        )

        assert pairs == []

    def test_drops_vetoed_pairs(self) -> None:
        left = _state(country_code="UA")
        right = _state(country_code="PL")

        pairs = _candidate_pairs(
            [left, right],
            families={},
            entities={left.id: {"kyiv"}, right.id: {"kyiv"}},
        )

        assert pairs == []


class TestSurvivor:
    def _pair(self, left: EventPairState, right: EventPairState):
        from hermes_worker.jobs.pair_score import PairScore

        return MagicMock(
            left=left,
            right=right,
            score=PairScore(score=0.9, components={}),
        )

    def test_prefers_more_members(self) -> None:
        left = _state(article_count=1)
        right = _state(article_count=5)

        survivor, loser = _survivor(self._pair(left, right), {})

        assert survivor is right
        assert loser is left

    def test_uses_updated_counts(self) -> None:
        left = _state(article_count=1)
        right = _state(article_count=1)

        survivor, loser = _survivor(
            self._pair(left, right),
            {left.id: 7, right.id: 2},
        )

        assert survivor is left
        assert loser is right

    def test_breaks_ties_by_older_first_report(self) -> None:
        older = _state(first_reported_at=NOW - timedelta(hours=2))
        newer = _state(first_reported_at=NOW)

        survivor, loser = _survivor(self._pair(newer, older), {})

        assert survivor is older
        assert loser is newer


class TestPairHash:
    def test_is_order_independent(self) -> None:
        left = _state()
        right = _state()
        pair = MagicMock(left=left, right=right)
        reversed_pair = MagicMock(left=right, right=left)

        assert _pair_hash(pair, "v1") == _pair_hash(reversed_pair, "v1")

    def test_changes_when_member_hash_changes(self) -> None:
        import dataclasses

        left = _state()
        right = _state()
        pair = MagicMock(left=left, right=right)
        baseline = _pair_hash(pair, "v1")

        changed = MagicMock(
            left=dataclasses.replace(left, member_hash="new-hash"),
            right=right,
        )

        assert _pair_hash(changed, "v1") != baseline

    def test_changes_when_prompt_version_changes(self) -> None:
        pair = MagicMock(left=_state(), right=_state())

        assert _pair_hash(pair, "v1") != _pair_hash(pair, "v2")


class TestEventSide:
    def test_includes_entities_and_location(self) -> None:
        side = _event_side(_state(), frozenset({"kyiv", "mayor"}))

        assert side.entities == ["kyiv", "mayor"]
        assert side.location == "Kyiv"
        assert side.fact is not None


class TestAdjudicationBudget:
    def test_stops_without_calling_llm_when_budget_is_empty(self) -> None:
        async def _test() -> None:
            adjudicator = MagicMock()
            adjudicator.prompt_version = "merge-v1"
            adjudicator.model_name = "test-model"
            adjudicator.decide = AsyncMock()
            ai = MagicMock()
            ai.adjudicator = adjudicator

            ctx, _session = _context(_settings(), budget=0, ai=ai)
            stage = ReconcileStage()
            state = MagicMock()
            state.adjudicated_pairs = 0
            from hermes_worker.jobs.context import StageStats

            state.stats = StageStats()

            pair = MagicMock()
            pair.left = _state()
            pair.right = _state()
            pair.left_entities = frozenset({"kyiv"})
            pair.right_entities = frozenset({"kyiv"})
            from hermes_worker.jobs.pair_score import PairScore

            pair.score = PairScore(
                score=0.88,
                components={},
                auto_threshold=0.92,
                gray_threshold=0.85,
            )

            with patch(
                "hermes_worker.jobs.stages.reconcile.ClusterDecisionService"
            ) as cache_cls:
                cache_cls.return_value.get = AsyncMock(return_value=None)
                decisions = await stage._adjudicate_gray(ctx, [pair], state)

            assert decisions == {}
            assert state.stats.counters["adjudication_budget_spent"] == 1
            adjudicator.decide.assert_not_awaited()

        asyncio.run(_test())


class TestReconcileRun:
    def test_returns_early_with_fewer_than_two_events(self) -> None:
        async def _test() -> None:
            ctx, _session = _context(_settings())

            with patch(
                "hermes_worker.jobs.stages.reconcile.EventMergeService"
            ) as service_cls:
                service = service_cls.return_value
                service.recent_states = AsyncMock(return_value=[_state()])
                service.family_sets = AsyncMock(return_value={})
                service.candidate_entities = AsyncMock(return_value={})

                stats = await ReconcileStage().run(ctx)

            assert stats.counters == {"events": 1}

        asyncio.run(_test())
