from __future__ import annotations
import hashlib
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import batched
from hermes_ai import (
    RelationshipDirection,
    RelationshipEvalInput,
    RelationshipEventSide,
    RelationshipKind,
)
from hermes_db.enums import (
    ClusterDecisionKind,
    EventRelationshipType,
    EventStatus,
    SelectionTier,
)
from hermes_db.models.event import Event
from hermes_db.services import (
    ClusterDecisionService,
    EventMergeService,
    EventRelationshipService,
    EventScoringService,
    RelationshipAnchorEvent,
    ThreadService,
    canonical_pair_key,
)
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_worker.jobs.actors import format_actor_label
from hermes_worker.jobs.context import (
    BudgetExhaustedError,
    JobContext,
    StageName,
    StageStats,
)
from hermes_worker.jobs.fingerprints import cosine_similarity
from hermes_worker.jobs.pair_score import _entities_compatible
from hermes_worker.jobs.runner import format_error


logger = logging.getLogger(__name__)

_PERSISTABLE_KINDS = frozenset(
    {
        RelationshipKind.CAUSED,
        RelationshipKind.FOLLOW_UP,
        RelationshipKind.REACTION,
        RelationshipKind.RELATED,
    }
)
_ENTITY_RECALL_MIN_COSINE = 0.50
MAX_ACTOR_NEIGHBORS_PER_EVENT = 6


@dataclass(frozen=True, slots=True)
class _CandidatePair:
    key: tuple[uuid.UUID, uuid.UUID]
    left: RelationshipAnchorEvent
    right: RelationshipAnchorEvent
    similarity: float
    entity_matches: int
    pair_hash: str


@dataclass(slots=True)
class _RunState:
    since: datetime
    merged_ids: set[uuid.UUID] = field(default_factory=set)
    stats: StageStats = field(default_factory=StageStats)


class RelationshipStage:
    name = StageName.RELATIONSHIP

    async def run(self, ctx: JobContext) -> StageStats:
        settings = ctx.settings
        now = datetime.now(UTC)
        state = _RunState(
            since=now - timedelta(days=settings.RELATIONSHIP_WINDOW_DAYS)
        )

        async with ctx.session_factory() as session:
            service = EventRelationshipService(session)
            anchors = await service.recent_anchor_events(
                since=state.since,
                limit=settings.RELATIONSHIP_EVENT_LIMIT,
            )
            state.stats.add("events", len(anchors))
            if len(anchors) < 2:
                return state.stats

            raw_pairs = await self._recall_pairs(
                ctx,
                service,
                anchors,
                since=state.since,
            )
            state.stats.add("pairs_recalled", len(raw_pairs))
            if not raw_pairs:
                return state.stats

            classifier = ctx.require_ai().relationships
            prompt_version = classifier.prompt_version
            ordered_pairs = [
                _build_candidate_pair(left, right, similarity, entity_matches, prompt_version)
                for (left, right), (similarity, entity_matches) in raw_pairs.items()
            ]
            existing_hashes = await service.existing_pair_hashes(
                [pair.key for pair in ordered_pairs]
            )
            cache = ClusterDecisionService(session)
            uncached: list[_CandidatePair] = []
            for pair in ordered_pairs:
                if existing_hashes.get(pair.key) == pair.pair_hash:
                    state.stats.add("skipped_existing")
                    continue
                if await cache.get(pair.pair_hash) is not None:
                    state.stats.add("skipped_cached")
                    continue
                uncached.append(pair)

        uncached.sort(
            key=lambda pair: (pair.similarity, pair.entity_matches),
            reverse=True,
        )
        allowed = uncached[: settings.RELATIONSHIP_LLM_PAIRS_PER_RUN]
        if len(allowed) < len(uncached):
            state.stats.add("pairs_deferred", len(uncached) - len(allowed))
        if not allowed:
            return state.stats

        await self._classify_and_persist(ctx, allowed, state)
        return state.stats

    async def _recall_pairs(
        self,
        ctx: JobContext,
        service: EventRelationshipService,
        anchors: Sequence[RelationshipAnchorEvent],
        *,
        since: datetime,
    ) -> dict[tuple[RelationshipAnchorEvent, RelationshipAnchorEvent], tuple[float, int]]:
        settings = ctx.settings
        pair_scores: dict[tuple[uuid.UUID, uuid.UUID], tuple[RelationshipAnchorEvent, RelationshipAnchorEvent, float, int]] = {}

        for anchor in anchors:
            neighbors = await service.neighbor_candidates(
                anchor,
                since=since,
                min_embedding_sim=settings.RELATIONSHIP_MIN_EMBEDDING_SIM,
                limit=settings.RELATIONSHIP_NEIGHBORS_PER_EVENT,
            )
            for neighbor in neighbors:
                if neighbor.id == anchor.id:
                    continue
                left, right = _ordered_pair(anchor, neighbor)
                key = canonical_pair_key(left.id, right.id)
                similarity = _pair_cosine(left, right)
                entity_matches = _soft_match_count(left.entities, right.entities)
                existing = pair_scores.get(key)
                if existing is None or similarity > existing[2]:
                    pair_scores[key] = (left, right, similarity, entity_matches)

        actor_candidate_buckets: dict[
            uuid.UUID,
            list[tuple[RelationshipAnchorEvent, RelationshipAnchorEvent, float, int]],
        ] = {}

        for idx, left_anchor in enumerate(anchors):
            has_entities = bool(left_anchor.entities)
            has_actors = bool(left_anchor.actor_keys)
            if not has_entities and not has_actors:
                continue
            for right_anchor in anchors[idx + 1 :]:
                entity_matches = (
                    _soft_match_count(left_anchor.entities, right_anchor.entities)
                    if has_entities and right_anchor.entities
                    else 0
                )
                actor_matches = (
                    _soft_match_count(left_anchor.actor_keys, right_anchor.actor_keys)
                    if has_actors and right_anchor.actor_keys
                    else 0
                )
                if entity_matches == 0 and actor_matches == 0:
                    continue
                similarity = _pair_cosine(left_anchor, right_anchor)
                left, right = _ordered_pair(left_anchor, right_anchor)
                key = canonical_pair_key(left.id, right.id)
                if key in pair_scores:
                    continue

                if actor_matches > 0:
                    combined = max(entity_matches, actor_matches)
                    actor_candidate_buckets.setdefault(left_anchor.id, []).append(
                        (left, right, similarity, combined)
                    )
                    actor_candidate_buckets.setdefault(right_anchor.id, []).append(
                        (left, right, similarity, combined)
                    )
                    continue

                has_both_embeddings = (
                    left_anchor.embedding is not None
                    and right_anchor.embedding is not None
                    and left_anchor.embedding_model == right_anchor.embedding_model
                )
                if (
                    entity_matches < 2
                    and has_both_embeddings
                    and similarity < _ENTITY_RECALL_MIN_COSINE
                ):
                    continue
                pair_scores[key] = (left, right, similarity, entity_matches)

        for candidates in actor_candidate_buckets.values():
            candidates.sort(key=lambda entry: (entry[3], entry[2]), reverse=True)
            for left, right, similarity, match_count in candidates[:MAX_ACTOR_NEIGHBORS_PER_EVENT]:
                key = canonical_pair_key(left.id, right.id)
                if key not in pair_scores:
                    pair_scores[key] = (left, right, similarity, match_count)

        return {
            (left, right): (similarity, entity_matches)
            for left, right, similarity, entity_matches in pair_scores.values()
        }

    async def _classify_and_persist(
        self,
        ctx: JobContext,
        pairs: Sequence[_CandidatePair],
        state: _RunState,
    ) -> None:
        settings = ctx.settings
        classifier = ctx.require_ai().relationships
        prompt_version = classifier.prompt_version

        for batch in batched(pairs, settings.RELATIONSHIP_BATCH_SIZE, strict=False):
            try:
                ctx.budget.reserve_llm_calls(1)
            except BudgetExhaustedError:
                state.stats.add("budget_exhausted")
                logger.warning("llm budget exhausted during relationship discovery.")
                break

            state.stats.add("classification_calls")
            inputs = [
                RelationshipEvalInput(
                    index=index,
                    left=_event_side(pair.left),
                    right=_event_side(pair.right),
                )
                for index, pair in enumerate(batch)
            ]
            response = await classifier.classify(inputs)
            if response is None:
                state.stats.add("classification_failed")
                continue

            by_index = {decision.index: decision for decision in response.decisions}
            try:
                async with ctx.session_factory() as session:
                    service = EventRelationshipService(session)
                    cache = ClusterDecisionService(session)
                    merge_service = EventMergeService(session)
                    for index, pair in enumerate(batch):
                        decision = by_index.get(index)
                        if decision is None:
                            state.stats.add("classification_missing")
                            continue

                        if (
                            pair.left.id in state.merged_ids
                            or pair.right.id in state.merged_ids
                        ):
                            continue

                        if decision.relationship == RelationshipKind.SAME_INCIDENT:
                            merged = await _try_auto_merge_same_incident(
                                session=session,
                                merge_service=merge_service,
                                pair=pair,
                                confidence=decision.confidence,
                                min_confidence=settings.RELATIONSHIP_MIN_CONFIDENCE,
                                merged_ids=state.merged_ids,
                            )
                            await cache.save(
                                pair_hash=pair.pair_hash,
                                decision=ClusterDecisionKind.SAME,
                                confidence=decision.confidence,
                                model=classifier.model_name,
                                prompt_version=prompt_version,
                            )
                            state.stats.add(
                                "merged_same_incident"
                                if merged
                                else "rejected_same_incident"
                            )
                            continue

                        if (
                            decision.relationship not in _PERSISTABLE_KINDS
                            or decision.confidence < settings.RELATIONSHIP_MIN_CONFIDENCE
                            or not decision.rationale.strip()
                        ):
                            await cache.save(
                                pair_hash=pair.pair_hash,
                                decision=ClusterDecisionKind.DIFFERENT,
                                confidence=decision.confidence,
                                model=classifier.model_name,
                                prompt_version=prompt_version,
                            )
                            state.stats.add("rejected_unrelated")
                            continue

                        source_id, target_id = (
                            (pair.right.id, pair.left.id)
                            if decision.direction == RelationshipDirection.RIGHT_TO_LEFT
                            else (pair.left.id, pair.right.id)
                        )
                        await service.upsert_relationship(
                            source_event_id=source_id,
                            target_event_id=target_id,
                            relationship_type=EventRelationshipType(
                                decision.relationship.value
                            ),
                            confidence=decision.confidence,
                            rationale=decision.rationale,
                            pair_hash=pair.pair_hash,
                        )
                        state.stats.add("relationships_saved")
                    await session.commit()
            except Exception as exc:
                logger.error(
                    "persisting relationship batch failed: %s.",
                    format_error(exc),
                    exc_info=True,
                )
                state.stats.add("persist_errors")


def _ordered_pair(
    left: RelationshipAnchorEvent,
    right: RelationshipAnchorEvent,
) -> tuple[RelationshipAnchorEvent, RelationshipAnchorEvent]:
    return (left, right) if left.id <= right.id else (right, left)


def _pair_cosine(
    left: RelationshipAnchorEvent,
    right: RelationshipAnchorEvent,
) -> float:
    if (
        left.embedding is None
        or right.embedding is None
        or left.embedding_model != right.embedding_model
    ):
        return 0.0
    return max(0.0, cosine_similarity(left.embedding, right.embedding))


def _soft_match_count(left: frozenset[str], right: frozenset[str]) -> int:
    matches = 0
    for l_item in left:
        if any(_entities_compatible(l_item, r_item) > 0.0 for r_item in right):
            matches += 1
    return matches


def _event_version_key(event: RelationshipAnchorEvent) -> str:
    base = event.member_hash or f"v{event.version}"
    if event.actor_keys:
        return f"{base}|actors={','.join(sorted(event.actor_keys))}"
    return base


def _build_candidate_pair(
    left: RelationshipAnchorEvent,
    right: RelationshipAnchorEvent,
    similarity: float,
    entity_matches: int,
    prompt_version: str,
) -> _CandidatePair:
    ordered_left, ordered_right = _ordered_pair(left, right)
    key = canonical_pair_key(ordered_left.id, ordered_right.id)
    payload = "|".join(
        [
            "rel",
            str(key[0]),
            str(key[1]),
            _event_version_key(ordered_left),
            _event_version_key(ordered_right),
            prompt_version,
        ]
    )
    pair_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return _CandidatePair(
        key=key,
        left=ordered_left,
        right=ordered_right,
        similarity=similarity,
        entity_matches=entity_matches,
        pair_hash=pair_hash,
    )


def _event_side(event: RelationshipAnchorEvent) -> RelationshipEventSide:
    occurred_at = event.event_time or event.latest_published_at or event.first_reported_at
    actors = [
        formatted
        for actor in event.actors[:8]
        if (formatted := format_actor_label(actor))
    ]
    return RelationshipEventSide(
        headline=event.ai_headline[:500],
        summary=event.ai_summary,
        entities=sorted(event.entities)[:10],
        actors=actors,
        location=event.location_name,
        country_code=event.country_code,
        occurred_at=occurred_at.isoformat(),
        category=event.category,
    )


async def _try_auto_merge_same_incident(
    *,
    session: AsyncSession,
    merge_service: EventMergeService,
    pair: _CandidatePair,
    confidence: float,
    min_confidence: float,
    merged_ids: set[uuid.UUID],
) -> bool:
    """Merge an unmerged SAME_INCIDENT pair only when live DB safety guards hold."""
    if confidence < min_confidence:
        return False
    left_ev = await session.get(Event, pair.left.id)
    right_ev = await session.get(Event, pair.right.id)
    if not _can_auto_merge(left_ev, right_ev, merged_ids):
        return False
    assert left_ev is not None and right_ev is not None

    survivor, loser = _pick_merge_survivor(left_ev, right_ev)
    moment = datetime.now(UTC)
    affected_threads = {
        tid for tid in (survivor.thread_id, loser.thread_id) if tid is not None
    }
    merged = await merge_service.merge(
        survivor_id=survivor.id,
        loser_id=loser.id,
        reason="rel:same_incident",
        now=moment,
    )
    if not merged:
        return False

    await EventScoringService(session).rescore(survivor.id, now=moment)
    if affected_threads:
        thread_service = ThreadService(session)
        for thread_id in affected_threads:
            await thread_service.recompute(thread_id, now=moment)
    merged_ids.add(loser.id)
    return True


def _can_auto_merge(
    left: Event | None,
    right: Event | None,
    merged_ids: set[uuid.UUID],
) -> bool:
    if left is None or right is None or left.id == right.id:
        return False
    if left.id in merged_ids or right.id in merged_ids:
        return False
    allowed_statuses = (EventStatus.ACTIVE, EventStatus.STALE)
    for event in (left, right):
        if event.merged_into_id is not None:
            return False
        if event.status not in allowed_statuses:
            return False
        if event.selection_tier == SelectionTier.DROP:
            return False
    return not (
        left.thread_id is not None
        and right.thread_id is not None
        and left.thread_id != right.thread_id
    )


def _pick_merge_survivor(left: Event, right: Event) -> tuple[Event, Event]:
    left_key = (
        left.article_count,
        float(left.importance_score),
        -(left.first_reported_at.timestamp()),
        -int(left.id.int),
    )
    right_key = (
        right.article_count,
        float(right.importance_score),
        -(right.first_reported_at.timestamp()),
        -int(right.id.int),
    )
    return (left, right) if left_key >= right_key else (right, left)
