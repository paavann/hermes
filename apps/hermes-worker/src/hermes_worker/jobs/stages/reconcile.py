from __future__ import annotations
import hashlib
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import batched
from hermes_ai import PairAdjudicationInput, PairSide
from hermes_db.enums import ClusterDecisionKind
from hermes_db.services import (
    ClusterDecisionService,
    EventMergeService,
    EventPairState,
    EventScoringService,
    ThreadService,
)
from hermes_worker.jobs.actors import actor_name_keys, format_actor_label
from hermes_worker.jobs.context import (
    BudgetExhaustedError,
    JobContext,
    StageName,
    StageStats,
)
from hermes_worker.jobs.pair_score import (
    MERGE_AUTO_THRESHOLD,
    MERGE_GRAY_THRESHOLD,
    PairScore,
    score_event_pair,
)
from hermes_worker.jobs.runner import format_error


logger = logging.getLogger(__name__)

ADJUDICATION_BATCH_SIZE = 10


@dataclass(frozen=True, slots=True)
class _EventPair:
    left: EventPairState
    right: EventPairState
    left_entities: frozenset[str]
    right_entities: frozenset[str]
    score: PairScore


@dataclass(slots=True)
class _RunState:
    now: datetime
    counts: dict[uuid.UUID, int]
    merged: set[uuid.UUID] = field(default_factory=set)
    adjudicated_pairs: int = 0
    stats: StageStats = field(default_factory=StageStats)


class ReconcileStage:
    """Merge duplicate events that survived clustering as separate pins."""

    name = StageName.RECONCILE

    async def run(self, ctx: JobContext) -> StageStats:
        state = _RunState(now=datetime.now(UTC), counts={})
        settings = ctx.settings
        since = state.now - timedelta(hours=settings.EVENT_RECONCILE_WINDOW_HOURS)

        async with ctx.session_factory() as session:
            service = EventMergeService(session)
            states = await service.recent_states(
                since=since,
                limit=settings.EVENT_RECONCILE_LIMIT,
            )
            event_ids = [item.id for item in states]
            families = await service.family_sets(event_ids)
            entities = await service.candidate_entities(event_ids)
        for item in states:
            if item.actors:
                entities.setdefault(item.id, set()).update(actor_name_keys(item.actors))
        state.counts = {item.id: item.article_count for item in states}
        state.stats.add("events", len(states))
        if len(states) < 2:
            return state.stats

        pairs = _candidate_pairs(states, families, entities)
        state.stats.add("pairs", len(pairs))
        if not pairs:
            return state.stats

        gray = [pair for pair in pairs if pair.score.score < MERGE_AUTO_THRESHOLD]
        decisions = await self._adjudicate_gray(ctx, gray, state)

        for pair in pairs:
            if pair.left.id in state.merged or pair.right.id in state.merged:
                continue
            if pair.score.score >= MERGE_AUTO_THRESHOLD:
                reason = "auto"
            else:
                decision = decisions.get((pair.left.id, pair.right.id))
                if decision is None or decision[0] != ClusterDecisionKind.SAME.value:
                    state.stats.add("merge_skipped_gray")
                    continue
                reason = "llm:same"
            try:
                merged = await self._merge(ctx, pair, reason, state)
            except Exception as exc:
                logger.error(
                    "merge %s/%s failed: %s.",
                    pair.left.id,
                    pair.right.id,
                    format_error(exc),
                    exc_info=True,
                )
                state.stats.add("merge_errors")
                continue
            if merged:
                state.stats.add("merged")
            else:
                state.stats.add("merge_noop")

        return state.stats

    async def _adjudicate_gray(
        self,
        ctx: JobContext,
        pairs: Sequence[_EventPair],
        state: _RunState,
    ) -> dict[tuple[uuid.UUID, uuid.UUID], tuple[str, float | None]]:
        if not pairs:
            return {}
        adjudicator = ctx.require_ai().adjudicator
        prompt_version = adjudicator.merge_prompt_version
        decisions: dict[tuple[uuid.UUID, uuid.UUID], tuple[str, float | None]] = {}
        uncached: list[_EventPair] = []

        async with ctx.session_factory() as session:
            cache = ClusterDecisionService(session)
            for pair in pairs:
                cached = await cache.get(_pair_hash(pair, prompt_version))
                if cached is None:
                    uncached.append(pair)
                    continue
                decisions[(pair.left.id, pair.right.id)] = (
                    cached.decision.value,
                    cached.confidence,
                )
                state.stats.add("adjudication_cached")

        remaining = ctx.settings.EVENT_MERGE_LLM_PAIRS_PER_RUN - state.adjudicated_pairs
        allowed = uncached[: max(0, remaining)]
        state.adjudicated_pairs += len(allowed)
        if len(allowed) < len(uncached):
            state.stats.add("adjudication_budget_spent")

        for batch in batched(allowed, ADJUDICATION_BATCH_SIZE, strict=False):
            inputs = [
                PairAdjudicationInput(
                    index=index,
                    left=_event_side(pair.left, pair.left_entities),
                    right=_event_side(pair.right, pair.right_entities),
                )
                for index, pair in enumerate(batch)
            ]
            try:
                ctx.budget.reserve_llm_calls(1)
            except BudgetExhaustedError:
                state.stats.add("adjudication_budget_spent")
                logger.warning("llm budget exhausted during event reconciliation.")
                break
            state.stats.add("adjudication_calls")
            response = await adjudicator.decide_merge(inputs)
            if response is None:
                state.stats.add("adjudication_failed")
                continue
            by_index = {decision.index: decision for decision in response.decisions}
            for index, pair in enumerate(batch):
                decision = by_index.get(index)
                if decision is None:
                    state.stats.add("adjudication_missing")
                    continue
                decisions[(pair.left.id, pair.right.id)] = (
                    decision.decision.value,
                    decision.confidence,
                )
                state.stats.add(f"decision_{decision.decision.value.lower()}")

        if decisions:
            async with ctx.session_factory() as session:
                cache = ClusterDecisionService(session)
                for pair in pairs:
                    decision = decisions.get((pair.left.id, pair.right.id))
                    if decision is None:
                        continue
                    await cache.save(
                        pair_hash=_pair_hash(pair, prompt_version),
                        decision=ClusterDecisionKind(decision[0]),
                        confidence=decision[1],
                        model=adjudicator.model_name,
                        prompt_version=prompt_version,
                    )
                await session.commit()

        return decisions

    async def _merge(
        self,
        ctx: JobContext,
        pair: _EventPair,
        reason: str,
        state: _RunState,
    ) -> bool:
        survivor, loser = _survivor(pair, state.counts)
        async with ctx.session_factory() as session:
            service = EventMergeService(session)
            affected_threads = {
                thread_id
                for thread_id in (survivor.thread_id, loser.thread_id)
                if thread_id is not None
            }
            merged = await service.merge(
                survivor_id=survivor.id,
                loser_id=loser.id,
                reason=reason,
                now=state.now,
            )
            if not merged:
                return False
            await EventScoringService(session).rescore(
                survivor.id,
                now=state.now,
            )
            thread_service = ThreadService(session)
            for thread_id in affected_threads:
                await thread_service.recompute(thread_id, now=state.now)
            await session.commit()

        state.merged.add(loser.id)
        state.counts[survivor.id] = state.counts.get(survivor.id, 0) + state.counts.get(
            loser.id, 0
        )
        state.stats.add(f"merge_{reason.split(':', 1)[0]}")
        return True


def _candidate_pairs(
    states: Sequence[EventPairState],
    families: dict[uuid.UUID, frozenset[uuid.UUID]],
    entities: dict[uuid.UUID, set[str]],
) -> list[_EventPair]:
    pairs: list[_EventPair] = []
    for index, left in enumerate(states):
        for right in states[index + 1 :]:
            left_entities = frozenset(entities.get(left.id, set()))
            right_entities = frozenset(entities.get(right.id, set()))
            shared = len(
                families.get(left.id, frozenset()) & families.get(right.id, frozenset())
            )
            score = score_event_pair(
                left,
                right,
                left_entities=left_entities,
                right_entities=right_entities,
                shared_families=shared,
            )
            if score.veto is not None or score.score < MERGE_GRAY_THRESHOLD:
                continue
            pairs.append(
                _EventPair(
                    left=left,
                    right=right,
                    left_entities=left_entities,
                    right_entities=right_entities,
                    score=score,
                )
            )
    pairs.sort(key=lambda pair: pair.score.score, reverse=True)
    return pairs


def _survivor(
    pair: _EventPair,
    counts: dict[uuid.UUID, int],
) -> tuple[EventPairState, EventPairState]:
    left_count = counts.get(pair.left.id, pair.left.article_count)
    right_count = counts.get(pair.right.id, pair.right.article_count)
    if left_count != right_count:
        return (
            (pair.left, pair.right)
            if left_count > right_count
            else (pair.right, pair.left)
        )
    if pair.left.first_reported_at <= pair.right.first_reported_at:
        return pair.left, pair.right
    return pair.right, pair.left


def _event_side(state: EventPairState, entities: frozenset[str]) -> PairSide:
    occurred_at = state.event_time or state.latest_published_at
    summary = state.ai_summary
    actors = [
        formatted
        for actor in state.actors[:8]
        if (formatted := format_actor_label(actor))
    ]
    return PairSide(
        headline=state.ai_headline[:500],
        fact=(summary or "")[:400] or None,
        summary=summary,
        entities=sorted(entities)[:8],
        actors=actors,
        location=state.location_name,
        occurred_at=occurred_at.isoformat() if occurred_at is not None else None,
        category=state.category,
    )


def _pair_hash(pair: _EventPair, prompt_version: str) -> str:
    ordered = sorted(
        (pair.left, pair.right),
        key=lambda state: state.id,
    )
    payload = "|".join(
        [
            "merge",
            str(ordered[0].id),
            str(ordered[1].id),
            ordered[0].member_hash or "none",
            ordered[1].member_hash or "none",
            prompt_version,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
