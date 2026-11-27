"""Tests for RelationshipStage candidate recall, caching, classification, and budgets."""

from __future__ import annotations
import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from hermes_ai import (
    RelationshipBatchResponse,
    RelationshipDecision,
    RelationshipDirection,
    RelationshipKind,
)
from hermes_db.enums import ClusterDecisionKind, EventRelationshipType
from hermes_db.services import RelationshipAnchorEvent, canonical_pair_key
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, LlmBudget, WorkerIdentity
from hermes_worker.jobs.stages.relationship import (
    RelationshipStage,
    _build_candidate_pair,
    _event_side,
)


NOW = datetime(2026, 11, 25, 12, 0, 0, tzinfo=UTC)


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "RELATIONSHIP_EVENT_LIMIT": 100,
        "RELATIONSHIP_WINDOW_DAYS": 10,
        "RELATIONSHIP_NEIGHBORS_PER_EVENT": 8,
        "RELATIONSHIP_MIN_EMBEDDING_SIM": 0.62,
        "RELATIONSHIP_MIN_CONFIDENCE": 0.70,
        "RELATIONSHIP_BATCH_SIZE": 8,
        "RELATIONSHIP_LLM_PAIRS_PER_RUN": 30,
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


def _anchor(
    *,
    event_id: uuid.UUID | None = None,
    headline: str = "Pakistani astronaut boards China space station",
    country_code: str | None = "CN",
    location_name: str | None = "China",
    category: str = "SCIENCE",
    entities: frozenset[str] = frozenset({"zeeshan ali", "tiangong"}),
    actors: tuple[dict[str, object], ...] = (),
    actor_keys: frozenset[str] | None = None,
    embedding: tuple[float, ...] | None = (1.0, 0.0, 0.0, 0.0),
    member_hash: str | None = "hash-a",
    version: int = 1,
    hours_offset: int = 0,
) -> RelationshipAnchorEvent:
    occurred = NOW + timedelta(hours=hours_offset)
    resolved_keys = (
        actor_keys
        if actor_keys is not None
        else frozenset(
            str(actor.get("name")).strip().casefold()
            for actor in actors
            if isinstance(actor.get("name"), str) and str(actor.get("name")).strip()
        )
    )
    return RelationshipAnchorEvent(
        id=event_id or uuid.uuid4(),
        ai_headline=headline,
        ai_summary=f"{headline} summary.",
        category=category,
        event_time=occurred,
        latest_published_at=occurred,
        first_reported_at=occurred,
        country_code=country_code,
        location_name=location_name,
        latitude=34.79,
        longitude=103.71,
        importance_score=45.0,
        embedding=embedding,
        embedding_model="test-embed" if embedding is not None else None,
        member_hash=member_hash,
        version=version,
        entities=entities,
        actors=actors,
        actor_keys=resolved_keys,
    )


def _ai_mock(classify_result: RelationshipBatchResponse | None = None) -> MagicMock:
    classifier = MagicMock()
    classifier.prompt_version = "relation-v1"
    classifier.model_name = "test-model"
    classifier.classify = AsyncMock(return_value=classify_result)
    return MagicMock(relationships=classifier)


class TestPairHashAndEventSide:
    def test_pair_hash_is_symmetric_and_versioned(self) -> None:
        left = _anchor(member_hash="hash-1", version=1)
        right = _anchor(member_hash="hash-2", version=1)

        ab = _build_candidate_pair(left, right, 0.72, 1, "relation-v1")
        ba = _build_candidate_pair(right, left, 0.72, 1, "relation-v1")
        assert ab.pair_hash == ba.pair_hash
        assert ab.key == canonical_pair_key(left.id, right.id)

        updated_right = _anchor(event_id=right.id, member_hash="hash-3", version=2)
        changed_member = _build_candidate_pair(
            left, updated_right, 0.72, 1, "relation-v1"
        )
        changed_prompt = _build_candidate_pair(left, right, 0.72, 1, "relation-v2")
        assert changed_member.pair_hash != ab.pair_hash
        assert changed_prompt.pair_hash != ab.pair_hash

        no_hash_v1 = _build_candidate_pair(
            _anchor(event_id=left.id, member_hash=None, version=1),
            right,
            0.72,
            1,
            "relation-v1",
        )
        no_hash_v2 = _build_candidate_pair(
            _anchor(event_id=left.id, member_hash=None, version=2),
            right,
            0.72,
            1,
            "relation-v1",
        )
        assert no_hash_v1.pair_hash != no_hash_v2.pair_hash

    def test_event_side_carries_entities_location_and_country(self) -> None:
        anchor = _anchor(
            country_code="PK",
            location_name="Islamabad, Pakistan",
            entities=frozenset({"suparco", "zeeshan ali"}),
        )
        side = _event_side(anchor)

        assert side.country_code == "PK"
        assert side.location == "Islamabad, Pakistan"
        assert side.entities == ["suparco", "zeeshan ali"]


class TestRelationshipRecall:
    def test_recalls_cross_country_vector_and_multi_entity_pairs(self) -> None:
        async def _test() -> None:
            china = _anchor(
                headline="Muhammad Zeeshan Ali boards Tiangong",
                country_code="CN",
                location_name="China",
                entities=frozenset({"muhammad zeeshan ali", "tiangong"}),
                embedding=(1.0, 0.0, 0.0, 0.0),
            )
            pakistan = _anchor(
                headline="SUPARCO crowd watches Zeeshan Ali board Tiangong",
                country_code="PK",
                location_name="Islamabad",
                entities=frozenset({"zeeshan ali", "tiangong", "suparco"}),
                embedding=(0.0, 1.0, 0.0, 0.0),
            )
            seoul = _anchor(
                headline="Air raid warning issued across Seoul",
                country_code="KR",
                location_name="Seoul",
                entities=frozenset({"south korea"}),
                embedding=(0.9, 0.435, 0.0, 0.0),
            )
            pyongyang = _anchor(
                headline="North Korea orders Swiss embassy closed",
                country_code="KP",
                location_name="Pyongyang",
                entities=frozenset({"north korea"}),
                embedding=(0.0, 0.0, 1.0, 0.0),
            )

            service = MagicMock()
            service.neighbor_candidates = AsyncMock(
                side_effect=lambda anchor, **_kwargs: (
                    [seoul] if anchor.id == china.id else []
                )
            )
            ctx, _session = _context(_settings())

            recalled = await RelationshipStage()._recall_pairs(
                ctx,
                service,
                [china, pakistan, seoul, pyongyang],
                since=NOW - timedelta(days=10),
            )

            recalled_keys = {
                canonical_pair_key(left_ev.id, right_ev.id)
                for (left_ev, right_ev) in recalled
            }
            assert canonical_pair_key(china.id, seoul.id) in recalled_keys
            assert canonical_pair_key(china.id, pakistan.id) in recalled_keys
            assert canonical_pair_key(china.id, pyongyang.id) not in recalled_keys

        asyncio.run(_test())

    def test_single_weak_entity_requires_min_cosine(self) -> None:
        async def _test() -> None:
            left = _anchor(
                entities=frozenset({"zeeshan ali"}),
                embedding=(1.0, 0.0, 0.0, 0.0),
            )
            low_cos = _anchor(
                entities=frozenset({"zeeshan ali"}),
                embedding=(0.3, 0.95, 0.0, 0.0),
            )
            mid_cos = _anchor(
                entities=frozenset({"zeeshan ali"}),
                embedding=(0.75, 0.66, 0.0, 0.0),
            )

            service = MagicMock()
            service.neighbor_candidates = AsyncMock(return_value=[])
            ctx, _session = _context(_settings())

            recalled = await RelationshipStage()._recall_pairs(
                ctx,
                service,
                [left, low_cos, mid_cos],
                since=NOW - timedelta(days=10),
            )

            recalled_keys = {
                canonical_pair_key(left_ev.id, right_ev.id)
                for (left_ev, right_ev) in recalled
            }
            assert canonical_pair_key(left.id, low_cos.id) not in recalled_keys
            assert canonical_pair_key(left.id, mid_cos.id) in recalled_keys

        asyncio.run(_test())

    def test_shared_primary_actor_recalls_cross_border_pair_below_entity_cosine(
        self,
    ) -> None:
        async def _test() -> None:
            gaza = _anchor(
                headline="Israeli attacks on Gaza kill eight",
                country_code="PS",
                location_name="Gaza Strip",
                category="CONFLICT",
                entities=frozenset(),
                actors=(
                    {
                        "name": "Israel",
                        "kind": "STATE",
                        "role": "ACTOR",
                        "location_name": "Israel",
                        "country_code": "IL",
                    },
                ),
                embedding=(1.0, 0.0, 0.0, 0.0),
            )
            israel = _anchor(
                headline="Israel institutionalises torture of Palestinian prisoners",
                country_code="IL",
                location_name="Israel",
                category="POLITICS",
                entities=frozenset(),
                actors=(
                    {
                        "name": "Israel",
                        "kind": "STATE",
                        "role": "ACTOR",
                        "location_name": "Israel",
                        "country_code": "IL",
                    },
                ),
                # ~0.25 cosine similarity, well below _ENTITY_RECALL_MIN_COSINE (0.50)
                embedding=(0.25, 0.968, 0.0, 0.0),
            )

            service = MagicMock()
            service.neighbor_candidates = AsyncMock(return_value=[])
            ctx, _session = _context(_settings())

            recalled = await RelationshipStage()._recall_pairs(
                ctx,
                service,
                [gaza, israel],
                since=NOW - timedelta(days=10),
            )

            assert canonical_pair_key(gaza.id, israel.id) in {
                canonical_pair_key(l_ev.id, r_ev.id) for (l_ev, r_ev) in recalled
            }
            assert _event_side(gaza).actors == ["Israel (STATE/ACTOR/IL)"]

        asyncio.run(_test())


class TestRelationshipStageRun:
    def test_returns_early_with_fewer_than_two_events(self) -> None:
        async def _test() -> None:
            ctx, _session = _context(_settings())

            with patch(
                "hermes_worker.jobs.stages.relationship.EventRelationshipService"
            ) as service_cls:
                service_cls.return_value.recent_anchor_events = AsyncMock(
                    return_value=[_anchor()]
                )
                stats = await RelationshipStage().run(ctx)

            assert stats.counters == {"events": 1}

        asyncio.run(_test())

    def test_skips_existing_cached_and_respects_pair_cap(self) -> None:
        async def _test() -> None:
            low_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            mid_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
            high_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
            fourth_id = uuid.UUID("00000000-0000-0000-0000-000000000004")

            e1 = _anchor(event_id=low_id, embedding=(1.0, 0.0, 0.0, 0.0))
            e2 = _anchor(event_id=mid_id, embedding=(0.8, 0.6, 0.0, 0.0))
            e3 = _anchor(event_id=high_id, embedding=(0.95, 0.31, 0.0, 0.0))
            e4 = _anchor(event_id=fourth_id, embedding=(0.7, 0.71, 0.0, 0.0))

            existing_pair = _build_candidate_pair(e1, e2, 0.8, 2, "relation-v1")
            cached_pair = _build_candidate_pair(e1, e4, 0.7, 2, "relation-v1")

            ai = _ai_mock(RelationshipBatchResponse(decisions=[]))
            ctx, _session = _context(
                _settings(RELATIONSHIP_LLM_PAIRS_PER_RUN=1),
                ai=ai,
            )

            with (
                patch(
                    "hermes_worker.jobs.stages.relationship.EventRelationshipService"
                ) as service_cls,
                patch(
                    "hermes_worker.jobs.stages.relationship.ClusterDecisionService"
                ) as cache_cls,
            ):
                service = service_cls.return_value
                service.recent_anchor_events = AsyncMock(return_value=[e1, e2, e3, e4])
                service.neighbor_candidates = AsyncMock(
                    side_effect=lambda anchor, **_kwargs: (
                        [e2, e3, e4] if anchor.id == e1.id else []
                    )
                )
                service.existing_pair_hashes = AsyncMock(
                    return_value={existing_pair.key: existing_pair.pair_hash}
                )
                cache_cls.return_value.get = AsyncMock(
                    side_effect=lambda h: (
                        SimpleNamespace(decision=ClusterDecisionKind.DIFFERENT)
                        if h == cached_pair.pair_hash
                        else None
                    )
                )

                stats = await RelationshipStage().run(ctx)

            assert stats.counters["skipped_existing"] == 1
            assert stats.counters["skipped_cached"] == 1
            ai.relationships.classify.assert_awaited_once()
            sent_inputs = ai.relationships.classify.await_args.args[0]
            assert len(sent_inputs) == 1

        asyncio.run(_test())

    def test_persists_direction_caches_same_incident_and_rejections(self) -> None:
        async def _test() -> None:
            a_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            b_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
            c_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
            d_id = uuid.UUID("00000000-0000-0000-0000-000000000004")

            e_a = _anchor(
                event_id=a_id,
                entities=frozenset(),
                embedding=(1.0, 0.0, 0.0, 0.0),
            )
            e_b = _anchor(
                event_id=b_id,
                country_code="PK",
                location_name="Islamabad",
                entities=frozenset(),
                embedding=(0.95, 0.31, 0.0, 0.0),
            )
            e_c = _anchor(
                event_id=c_id,
                entities=frozenset(),
                embedding=(0.85, 0.52, 0.0, 0.0),
            )
            e_d = _anchor(
                event_id=d_id,
                entities=frozenset(),
                embedding=(0.75, 0.66, 0.0, 0.0),
            )

            ai = _ai_mock(
                RelationshipBatchResponse(
                    decisions=[
                        RelationshipDecision(
                            index=0,
                            relationship=RelationshipKind.REACTION,
                            direction=RelationshipDirection.RIGHT_TO_LEFT,
                            confidence=0.91,
                            rationale="Islamabad crowd gathered after the launch.",
                        ),
                        RelationshipDecision(
                            index=1,
                            relationship=RelationshipKind.SAME_INCIDENT,
                            direction=RelationshipDirection.BIDIRECTIONAL,
                            confidence=0.88,
                            rationale="Both cover the identical boarding incident.",
                        ),
                        RelationshipDecision(
                            index=2,
                            relationship=RelationshipKind.NONE,
                            direction=RelationshipDirection.BIDIRECTIONAL,
                            confidence=0.80,
                            rationale="Unrelated regional stories.",
                        ),
                    ]
                )
            )
            ctx, session = _context(_settings(), ai=ai)

            with (
                patch(
                    "hermes_worker.jobs.stages.relationship.EventRelationshipService"
                ) as service_cls,
                patch(
                    "hermes_worker.jobs.stages.relationship.ClusterDecisionService"
                ) as cache_cls,
            ):
                service = service_cls.return_value
                service.recent_anchor_events = AsyncMock(
                    return_value=[e_a, e_b, e_c, e_d]
                )
                service.neighbor_candidates = AsyncMock(
                    side_effect=lambda anchor, **_kwargs: (
                        [e_b, e_c, e_d] if anchor.id == e_a.id else []
                    )
                )
                service.existing_pair_hashes = AsyncMock(return_value={})
                service.upsert_relationship = AsyncMock()

                cache = cache_cls.return_value
                cache.get = AsyncMock(return_value=None)
                cache.save = AsyncMock()

                stats = await RelationshipStage().run(ctx)

            assert stats.counters["relationships_saved"] == 1
            assert stats.counters["rejected_same_incident"] == 1
            assert stats.counters["rejected_unrelated"] == 1

            upsert_kwargs = service.upsert_relationship.await_args.kwargs
            assert upsert_kwargs["source_event_id"] == b_id
            assert upsert_kwargs["target_event_id"] == a_id
            assert upsert_kwargs["relationship_type"] == EventRelationshipType.REACTION
            assert upsert_kwargs["confidence"] == 0.91

            saved_decisions = [call.kwargs["decision"] for call in cache.save.await_args_list]
            assert saved_decisions == [
                ClusterDecisionKind.SAME,
                ClusterDecisionKind.DIFFERENT,
            ]
            session.commit.assert_awaited()

        asyncio.run(_test())

    def test_stops_cleanly_when_budget_is_exhausted(self) -> None:
        async def _test() -> None:
            e_a = _anchor(event_id=uuid.uuid4(), embedding=(1.0, 0.0, 0.0, 0.0))
            e_b = _anchor(event_id=uuid.uuid4(), embedding=(0.9, 0.435, 0.0, 0.0))
            ai = _ai_mock()
            ctx, _session = _context(_settings(), budget=0, ai=ai)

            with (
                patch(
                    "hermes_worker.jobs.stages.relationship.EventRelationshipService"
                ) as service_cls,
                patch(
                    "hermes_worker.jobs.stages.relationship.ClusterDecisionService"
                ) as cache_cls,
            ):
                service = service_cls.return_value
                service.recent_anchor_events = AsyncMock(return_value=[e_a, e_b])
                service.neighbor_candidates = AsyncMock(return_value=[e_b])
                service.existing_pair_hashes = AsyncMock(return_value={})
                cache_cls.return_value.get = AsyncMock(return_value=None)

                stats = await RelationshipStage().run(ctx)

            assert stats.counters["budget_exhausted"] == 1
            ai.relationships.classify.assert_not_awaited()

        asyncio.run(_test())

    def test_auto_merges_safe_same_incident_and_skips_thread_conflict(self) -> None:
        async def _test() -> None:
            from hermes_db.enums import EventStatus, SelectionTier

            a_id = uuid.UUID("00000000-0000-0000-0000-000000000011")
            b_id = uuid.UUID("00000000-0000-0000-0000-000000000012")
            c_id = uuid.UUID("00000000-0000-0000-0000-000000000013")
            d_id = uuid.UUID("00000000-0000-0000-0000-000000000014")

            e_a = _anchor(
                event_id=a_id,
                entities=frozenset(),
                embedding=(1.0, 0.0, 0.0, 0.0),
            )
            e_b = _anchor(
                event_id=b_id,
                entities=frozenset(),
                embedding=(0.95, 0.31, 0.0, 0.0),
            )
            e_c = _anchor(
                event_id=c_id,
                entities=frozenset(),
                embedding=(0.0, 0.0, 1.0, 0.0),
            )
            e_d = _anchor(
                event_id=d_id,
                entities=frozenset(),
                embedding=(0.0, 0.0, 0.90, 0.43),
            )

            def _live_event(
                event_id: uuid.UUID,
                *,
                article_count: int,
                importance_score: float,
                thread_id: uuid.UUID | None,
                hours_offset: int = 0,
            ) -> MagicMock:
                ev = MagicMock()
                ev.id = event_id
                ev.merged_into_id = None
                ev.status = EventStatus.ACTIVE
                ev.selection_tier = SelectionTier.PRIMARY
                ev.thread_id = thread_id
                ev.article_count = article_count
                ev.importance_score = importance_score
                ev.first_reported_at = NOW + timedelta(hours=hours_offset)
                return ev

            ev_a = _live_event(a_id, article_count=2, importance_score=50.0, thread_id=None)
            ev_b = _live_event(
                b_id,
                article_count=1,
                importance_score=30.0,
                thread_id=None,
                hours_offset=1,
            )
            ev_c = _live_event(
                c_id, article_count=2, importance_score=50.0, thread_id=uuid.uuid4()
            )
            ev_d = _live_event(
                d_id, article_count=3, importance_score=60.0, thread_id=uuid.uuid4()
            )

            ai = _ai_mock(
                RelationshipBatchResponse(
                    decisions=[
                        RelationshipDecision(
                            index=0,
                            relationship=RelationshipKind.SAME_INCIDENT,
                            direction=RelationshipDirection.BIDIRECTIONAL,
                            confidence=0.92,
                            rationale="Same ONS 77,000 report.",
                        ),
                        RelationshipDecision(
                            index=1,
                            relationship=RelationshipKind.SAME_INCIDENT,
                            direction=RelationshipDirection.BIDIRECTIONAL,
                            confidence=0.88,
                            rationale="Conflicting thread safeguard test.",
                        ),
                    ]
                )
            )
            ctx, session = _context(_settings(), ai=ai)
            session.get = AsyncMock(side_effect=[ev_a, ev_b, ev_c, ev_d])

            with (
                patch(
                    "hermes_worker.jobs.stages.relationship.EventRelationshipService"
                ) as service_cls,
                patch(
                    "hermes_worker.jobs.stages.relationship.ClusterDecisionService"
                ) as cache_cls,
                patch(
                    "hermes_worker.jobs.stages.relationship.EventMergeService"
                ) as merge_cls,
                patch(
                    "hermes_worker.jobs.stages.relationship.EventScoringService"
                ) as scoring_cls,
            ):
                service = service_cls.return_value
                service.recent_anchor_events = AsyncMock(
                    return_value=[e_a, e_b, e_c, e_d]
                )
                service.neighbor_candidates = AsyncMock(
                    side_effect=lambda anchor, **_kwargs: (
                        [e_b]
                        if anchor.id == a_id
                        else ([e_d] if anchor.id == c_id else [])
                    )
                )
                service.existing_pair_hashes = AsyncMock(return_value={})
                service.upsert_relationship = AsyncMock()
                cache_cls.return_value.get = AsyncMock(return_value=None)
                cache_cls.return_value.save = AsyncMock()
                merge_cls.return_value.merge = AsyncMock(return_value=True)
                scoring_cls.return_value.rescore = AsyncMock()

                stats = await RelationshipStage().run(ctx)

            assert stats.counters["merged_same_incident"] == 1
            assert stats.counters["rejected_same_incident"] == 1
            merge_cls.return_value.merge.assert_awaited_once_with(
                survivor_id=a_id,
                loser_id=b_id,
                reason="rel:same_incident",
                now=merge_cls.return_value.merge.await_args.kwargs["now"],
            )
            scoring_cls.return_value.rescore.assert_awaited_once()
            service.upsert_relationship.assert_not_awaited()

        asyncio.run(_test())
