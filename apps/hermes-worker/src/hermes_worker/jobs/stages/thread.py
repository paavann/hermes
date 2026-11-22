from __future__ import annotations
import hashlib
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import batched
from hermes_ai import (
    PREDEFINED_CATEGORIES,
    ThreadAssignmentInput,
    ThreadDecision,
    ThreadEventSide,
    ThreadSide,
)
from hermes_db.enums import ClusterDecisionKind, ThreadKind
from hermes_db.services import (
    ClusterDecisionService,
    ThreadEventSnapshot,
    ThreadMatch,
    ThreadService,
)
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_worker.jobs.context import (
    BudgetExhaustedError,
    JobContext,
    StageName,
    StageStats,
)
from hermes_worker.jobs.runner import format_error


logger = logging.getLogger(__name__)

THREAD_AUTO_THRESHOLD = 0.85
THREAD_GRAY_THRESHOLD = 0.70
MAX_GRAY_CANDIDATES = 3
MAX_NEW_THREADS_PER_RUN = 10
DEVELOPING_WINDOW_HOURS = 72


@dataclass(frozen=True, slots=True)
class _PendingEvent:
    event: ThreadEventSnapshot
    matches: tuple[ThreadMatch, ...]


@dataclass(frozen=True, slots=True)
class _Decision:
    kind: ThreadDecision
    confidence: float


@dataclass(slots=True)
class _RunState:
    now: datetime
    adjudicated_pairs: int = 0
    assigned: set[uuid.UUID] = field(default_factory=set)
    stats: StageStats = field(default_factory=StageStats)


class ThreadStage:
    """Attach events to persistent story threads and create new ones."""

    name = StageName.THREAD

    async def run(self, ctx: JobContext) -> StageStats:
        state = _RunState(now=datetime.now(UTC))
        async with ctx.session_factory() as session:
            events = await ThreadService(session).unthreaded_events(
                limit=ctx.settings.THREAD_EVENT_LIMIT
            )
        state.stats.add("unthreaded", len(events))
        if not events:
            return state.stats

        pending: list[_PendingEvent] = []
        async with ctx.session_factory() as session:
            service = ThreadService(session)
            for event in events:
                matches = await service.ranked_candidates(
                    event,
                    limit=ctx.settings.THREAD_CANDIDATE_LIMIT,
                )
                best = matches[0] if matches else None
                if best is not None and best.score >= THREAD_AUTO_THRESHOLD:
                    await self._assign(session, event, best.candidate.id, state)
                    state.stats.add("assigned_auto")
                elif best is not None and best.score >= THREAD_GRAY_THRESHOLD:
                    pending.append(
                        _PendingEvent(
                            event=event,
                            matches=tuple(matches[:MAX_GRAY_CANDIDATES]),
                        )
                    )
                else:
                    state.stats.add("unmatched")
            await session.commit()

        if pending:
            try:
                await self._resolve_pending(ctx, pending, state)
            except BudgetExhaustedError:
                state.stats.add("budget_exhausted")
                logger.warning("llm budget exhausted during thread assignment.")

        remaining = [event for event in events if event.id not in state.assigned]
        await self._create_threads(ctx, remaining, state)
        return state.stats

    async def _resolve_pending(
        self,
        ctx: JobContext,
        pending: Sequence[_PendingEvent],
        state: _RunState,
    ) -> None:
        assigner = ctx.require_ai().threads
        prompt_version = assigner.prompt_version
        decisions: dict[tuple[uuid.UUID, uuid.UUID], _Decision] = {}
        uncached: list[tuple[ThreadEventSnapshot, ThreadMatch]] = []

        async with ctx.session_factory() as session:
            cache = ClusterDecisionService(session)
            for item in pending:
                for match in item.matches:
                    key = (item.event.id, match.candidate.id)
                    cached = await cache.get(
                        _pair_hash(item.event.id, match.candidate, prompt_version)
                    )
                    if cached is None:
                        uncached.append((item.event, match))
                        continue
                    decisions[key] = _Decision(
                        kind=ThreadDecision(cached.decision.value),
                        confidence=cached.confidence or 0.0,
                    )
                    state.stats.add("adjudication_cached")

        if uncached:
            await self._adjudicate(ctx, uncached, prompt_version, state, decisions)
            async with ctx.session_factory() as session:
                cache = ClusterDecisionService(session)
                for (event_id, thread_id), decision in decisions.items():
                    candidate = _find_candidate(pending, thread_id)
                    if candidate is None:
                        continue
                    await cache.save(
                        pair_hash=_pair_hash(event_id, candidate, prompt_version),
                        decision=ClusterDecisionKind(decision.kind.value),
                        confidence=decision.confidence,
                        model=assigner.model_name,
                        prompt_version=prompt_version,
                    )
                await session.commit()

        async with ctx.session_factory() as session:
            for item in pending:
                chosen: tuple[ThreadMatch, _Decision] | None = None
                for match in item.matches:
                    decision = decisions.get((item.event.id, match.candidate.id))
                    if decision is None or decision.kind != ThreadDecision.SAME:
                        continue
                    if chosen is None or match.score > chosen[0].score:
                        chosen = (match, decision)
                if chosen is None:
                    continue
                await self._assign(
                    session,
                    item.event,
                    chosen[0].candidate.id,
                    state,
                )
                state.stats.add("assigned_llm")
            await session.commit()

    async def _adjudicate(
        self,
        ctx: JobContext,
        pairs: Sequence[tuple[ThreadEventSnapshot, ThreadMatch]],
        prompt_version: str,
        state: _RunState,
        decisions: dict[tuple[uuid.UUID, uuid.UUID], _Decision],
    ) -> None:
        remaining = ctx.settings.THREAD_LLM_PAIRS_PER_RUN - state.adjudicated_pairs
        if remaining <= 0:
            state.stats.add("adjudication_budget_spent")
            return
        allowed = list(pairs)[:remaining]
        state.adjudicated_pairs += len(allowed)
        assigner = ctx.require_ai().threads
        for batch in batched(
            allowed,
            ctx.settings.THREAD_ADJUDICATION_BATCH_SIZE,
            strict=False,
        ):
            inputs = [
                ThreadAssignmentInput(
                    index=index,
                    event=_event_side(event),
                    thread=_thread_side(match),
                )
                for index, (event, match) in enumerate(batch)
            ]
            ctx.budget.reserve_llm_calls(1)
            state.stats.add("adjudication_calls")
            response = await assigner.assign(inputs)
            if response is None:
                state.stats.add("adjudication_failed")
                continue
            by_index = {decision.index: decision for decision in response.decisions}
            for index, (event, match) in enumerate(batch):
                decision = by_index.get(index)
                if decision is None:
                    state.stats.add("adjudication_missing")
                    continue
                decisions[(event.id, match.candidate.id)] = _Decision(
                    kind=decision.decision,
                    confidence=decision.confidence,
                )
                state.stats.add(f"decision_{decision.decision.value.lower()}")

    async def _assign(
        self,
        session: AsyncSession,
        event: ThreadEventSnapshot,
        thread_id: uuid.UUID,
        state: _RunState,
    ) -> None:
        await ThreadService(session).assign_event(
            event.id,
            thread_id,
            now=state.now,
        )
        state.assigned.add(event.id)

    async def _create_threads(
        self,
        ctx: JobContext,
        events: Sequence[ThreadEventSnapshot],
        state: _RunState,
    ) -> None:
        groups: dict[tuple[str, ...], list[ThreadEventSnapshot]] = {}
        for event in events:
            key = _group_key(event)
            if key is None:
                state.stats.add("ungrouped")
                continue
            groups.setdefault(key, []).append(event)

        eligible = sorted(
            (
                group
                for group in groups.values()
                if len(group) >= ctx.settings.THREAD_MIN_GROUP
            ),
            key=lambda group: (-len(group), group[0].id),
        )[:MAX_NEW_THREADS_PER_RUN]

        async with ctx.session_factory() as session:
            service = ThreadService(session)
            for group in eligible:
                try:
                    thread = await self._create_thread(service, group, state)
                except Exception as exc:
                    logger.error(
                        "thread creation failed: %s.",
                        format_error(exc),
                        exc_info=True,
                    )
                    state.stats.add("thread_errors")
                    continue
                for event in group:
                    await service.assign_event(event.id, thread.id, now=state.now)
                state.stats.add("threads_created")
                state.stats.add("events_grouped", len(group))
            await session.commit()

    async def _create_thread(
        self,
        service: ThreadService,
        group: Sequence[ThreadEventSnapshot],
        state: _RunState,
    ):
        ordered = sorted(group, key=lambda event: event.importance_score, reverse=True)
        lead = ordered[0]
        entities = _group_entities(group)
        display = PREDEFINED_CATEGORIES.get(lead.category, {}).get(
            "display_name",
            lead.category,
        )
        name = (
            f"{entities[0].title()} — {display}"
            if entities
            else f"{display} — {lead.ai_headline[:120]}"
        )
        timestamps = [
            event.latest_published_at or event.event_time or event.first_reported_at
            for event in group
        ]
        latest = max(timestamps)
        earliest = min(timestamps)
        span = latest - earliest
        embedding, model = _centroid(group)
        thread = await service.create_thread(
            name,
            kind=(
                ThreadKind.DEVELOPING
                if span <= timedelta(hours=DEVELOPING_WINDOW_HOURS)
                else ThreadKind.TOPIC
            ),
            description=(lead.ai_summary or lead.ai_headline)[:1_500],
            entities=[{"name": entity, "kind": "OTHER"} for entity in entities[:12]],
            started_at=earliest,
            embedding=embedding,
            embedding_model=model,
            last_event_at=latest,
        )
        state.stats.add(f"thread_kind_{thread.kind.value.lower()}")
        return thread


def _group_key(event: ThreadEventSnapshot) -> tuple[str, ...] | None:
    entities = sorted(event.entities)
    if not entities:
        return None
    if len(entities) >= 2:
        return (event.category, entities[0], entities[1])
    return (event.category, entities[0])


def _group_entities(group: Sequence[ThreadEventSnapshot]) -> list[str]:
    counts: dict[str, int] = {}
    for event in group:
        for entity in event.entities:
            counts[entity] = counts.get(entity, 0) + 1
    shared = [(entity, count) for entity, count in counts.items() if count >= 2]
    shared.sort(key=lambda item: (-item[1], item[0]))
    return [entity for entity, _count in shared[:3]]


def _centroid(
    group: Sequence[ThreadEventSnapshot],
) -> tuple[list[float] | None, str | None]:
    vectors = [
        event.embedding
        for event in group
        if event.embedding is not None and event.embedding_model is not None
    ]
    if not vectors:
        return None, None
    model = next(
        event.embedding_model
        for event in group
        if event.embedding is not None and event.embedding_model is not None
    )
    width = len(vectors[0])
    centroid = [
        sum(vector[index] for vector in vectors) / len(vectors)
        for index in range(width)
    ]
    return centroid, model


def _find_candidate(
    pending: Sequence[_PendingEvent],
    thread_id: uuid.UUID,
) -> ThreadMatch | None:
    for item in pending:
        for match in item.matches:
            if match.candidate.id == thread_id:
                return match
    return None


def _pair_hash(
    event_id: uuid.UUID,
    candidate: ThreadMatch,
    prompt_version: str,
) -> str:
    last_event_at = (
        candidate.candidate.last_event_at.isoformat()
        if candidate.candidate.last_event_at is not None
        else "none"
    )
    payload = "|".join(
        [
            "thread",
            str(event_id),
            str(candidate.candidate.id),
            last_event_at,
            prompt_version,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _event_side(event: ThreadEventSnapshot) -> ThreadEventSide:
    location = event.locations[0] if event.locations else None
    occurred_at = event.event_time or event.latest_published_at
    return ThreadEventSide(
        headline=event.ai_headline[:500],
        summary=event.ai_summary,
        entities=sorted(event.entities)[:8],
        location=location,
        occurred_at=occurred_at.isoformat() if occurred_at is not None else None,
        category=event.category,
    )


def _thread_side(match: ThreadMatch) -> ThreadSide:
    candidate = match.candidate
    return ThreadSide(
        name=candidate.name,
        description=candidate.description,
        entities=sorted(candidate.entities)[:12],
        last_event_at=(
            candidate.last_event_at.isoformat()
            if candidate.last_event_at is not None
            else None
        ),
        event_count=candidate.event_count,
    )
