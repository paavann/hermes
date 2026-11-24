from __future__ import annotations
import hashlib
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import batched
from hermes_ai import (
    DEFAULT_CATEGORY_COLOR,
    PREDEFINED_CATEGORIES,
    PairAdjudicationInput,
    PairSide,
)
from hermes_db.enums import (
    AssignmentMethod,
    ClusterDecisionKind,
    EventScope,
    ImpactLevel,
    IngestStatus,
)
from hermes_db.models.event import Event
from hermes_db.services import (
    ArticleAnalysisService,
    AssignableArticle,
    ClusterDecisionService,
    EventAssignmentService,
    EventCandidate,
    EventMembershipService,
)
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_worker.jobs.context import (
    BudgetExhaustedError,
    JobContext,
    StageName,
    StageStats,
)
from hermes_worker.jobs.pair_score import (
    AUTO_ATTACH_THRESHOLD,
    LLM_BAND_THRESHOLD,
    GeoLocation,
    PairScore,
    score_pair,
)
from hermes_worker.jobs.runner import format_error


logger = logging.getLogger(__name__)

MAX_ADJUDICATED_PAIRS_PER_ARTICLE = 3


@dataclass(frozen=True, slots=True)
class _PendingArticle:
    article: AssignableArticle
    candidates: tuple[tuple[EventCandidate, PairScore], ...]


@dataclass(slots=True)
class _RunState:
    since: datetime
    now: datetime
    adjudicated_pairs: int = 0
    stats: StageStats = field(default_factory=StageStats)


@dataclass(frozen=True, slots=True)
class _Decision:
    kind: ClusterDecisionKind
    confidence: float


class ClusterStage:
    """Assign analyzed articles to incident-level events."""

    name = StageName.CLUSTER

    async def run(self, ctx: JobContext) -> StageStats:
        settings = ctx.settings
        state = _RunState(
            since=datetime.now(UTC)
            - timedelta(days=settings.EVENT_CLUSTER_WINDOW_DAYS),
            now=datetime.now(UTC),
        )

        async with ctx.session_factory() as session:
            articles = await EventAssignmentService(session).unclustered_articles(
                limit=settings.EVENT_CLUSTER_BATCH_SIZE
            )
        state.stats.add("articles", len(articles))
        if not articles:
            return state.stats

        for wave in batched(articles, settings.EVENT_CLUSTER_WAVE_SIZE, strict=False):
            try:
                await self._process_wave(ctx, list(wave), state)
            except BudgetExhaustedError:
                state.stats.add("budget_exhausted")
                logger.warning("llm budget exhausted during clustering.")
                return state.stats
            except Exception as exc:
                logger.error(
                    "cluster wave failed: %s.",
                    format_error(exc),
                    exc_info=True,
                )
                state.stats.add("wave_errors")
        return state.stats

    async def _process_wave(
        self,
        ctx: JobContext,
        articles: Sequence[AssignableArticle],
        state: _RunState,
    ) -> None:
        pending: list[_PendingArticle] = []

        async with ctx.session_factory() as session:
            for article in articles:
                try:
                    await self._classify_article(
                        ctx,
                        session,
                        article,
                        state,
                        pending,
                    )
                except Exception as exc:
                    logger.error(
                        "cluster article %s failed: %s.",
                        article.id,
                        format_error(exc),
                        exc_info=True,
                    )
                    state.stats.add("article_errors")
            await session.commit()

        if pending:
            await self._resolve_pending(ctx, pending, state)

    async def _classify_article(
        self,
        ctx: JobContext,
        session: AsyncSession,
        article: AssignableArticle,
        state: _RunState,
        pending: list[_PendingArticle],
    ) -> None:
        settings = ctx.settings
        assignment = EventAssignmentService(session)
        candidates = await assignment.candidates(
            article,
            since=state.since,
            ann_limit=settings.EVENT_CLUSTER_ANN_LIMIT,
            country_limit=settings.EVENT_CLUSTER_COUNTRY_LIMIT,
            cap=settings.EVENT_CLUSTER_CANDIDATE_CAP,
        )
        scored = [
            (candidate, score)
            for candidate in candidates
            if (
                score := score_pair(
                    article,
                    candidate,
                    article_location=_article_location(article),
                )
            ).veto
            is None
        ]
        scored.sort(key=lambda item: item[1].score, reverse=True)
        best = scored[0] if scored else None

        if best is not None and best[1].score >= AUTO_ATTACH_THRESHOLD:
            await self._attach(
                ctx,
                session,
                article,
                best[0],
                best[1],
                method=AssignmentMethod.AUTO,
                state=state,
            )
            return

        if best is not None and best[1].score >= LLM_BAND_THRESHOLD:
            pending.append(
                _PendingArticle(
                    article=article,
                    candidates=tuple(scored[:MAX_ADJUDICATED_PAIRS_PER_ARTICLE]),
                )
            )
            return

        await self._create(ctx, session, article, state)

    async def _resolve_pending(
        self,
        ctx: JobContext,
        pending: Sequence[_PendingArticle],
        state: _RunState,
    ) -> None:
        adjudicator = ctx.require_ai().adjudicator
        prompt_version = adjudicator.prompt_version
        decisions: dict[tuple[uuid.UUID, uuid.UUID], _Decision] = {}
        uncached: list[tuple[AssignableArticle, EventCandidate]] = []

        async with ctx.session_factory() as session:
            cache = ClusterDecisionService(session)
            for item in pending:
                for candidate, _score in item.candidates:
                    key = (item.article.id, candidate.id)
                    cached = await cache.get(
                        _pair_hash(item.article.id, candidate, prompt_version)
                    )
                    if cached is None:
                        uncached.append((item.article, candidate))
                        continue
                    decisions[key] = _Decision(
                        kind=cached.decision,
                        confidence=cached.confidence or 0.0,
                    )
                    state.stats.add("adjudication_cached")

        if uncached:
            await self._adjudicate(ctx, uncached, prompt_version, state, decisions)
            async with ctx.session_factory() as session:
                cache = ClusterDecisionService(session)
                for (article_id, candidate_id), decision in decisions.items():
                    candidate = _find_candidate(pending, candidate_id)
                    if candidate is None:
                        continue
                    await cache.save(
                        pair_hash=_pair_hash(
                            article_id,
                            candidate,
                            prompt_version,
                        ),
                        decision=decision.kind,
                        confidence=decision.confidence,
                        model=adjudicator.model_name,
                        prompt_version=prompt_version,
                    )
                await session.commit()

        async with ctx.session_factory() as session:
            for item in pending:
                chosen: tuple[EventCandidate, PairScore, _Decision] | None = None
                for candidate, score in item.candidates:
                    decision = decisions.get((item.article.id, candidate.id))
                    if decision is None or decision.kind != ClusterDecisionKind.SAME:
                        continue
                    if chosen is None or score.score > chosen[1].score:
                        chosen = (candidate, score, decision)
                if chosen is None:
                    await self._create(ctx, session, item.article, state)
                else:
                    await self._attach(
                        ctx,
                        session,
                        item.article,
                        chosen[0],
                        chosen[1],
                        method=AssignmentMethod.LLM,
                        state=state,
                        confidence=chosen[2].confidence,
                    )
            await session.commit()

    async def _adjudicate(
        self,
        ctx: JobContext,
        pairs: Sequence[tuple[AssignableArticle, EventCandidate]],
        prompt_version: str,
        state: _RunState,
        decisions: dict[tuple[uuid.UUID, uuid.UUID], _Decision],
    ) -> None:
        remaining = (
            ctx.settings.EVENT_CLUSTER_LLM_PAIRS_PER_RUN - state.adjudicated_pairs
        )
        if remaining <= 0:
            state.stats.add("adjudication_budget_spent")
            return

        allowed = list(pairs)[:remaining]
        state.adjudicated_pairs += len(allowed)
        adjudicator = ctx.require_ai().adjudicator
        for batch in batched(
            allowed,
            ctx.settings.EVENT_CLUSTER_ADJUDICATION_BATCH_SIZE,
            strict=False,
        ):
            inputs = [
                PairAdjudicationInput(
                    index=index,
                    left=_article_side(article),
                    right=_event_side(candidate),
                )
                for index, (article, candidate) in enumerate(batch)
            ]
            ctx.budget.reserve_llm_calls(1)
            state.stats.add("adjudication_calls")
            response = await adjudicator.decide(inputs)
            if response is None:
                state.stats.add("adjudication_failed")
                continue
            by_index = {decision.index: decision for decision in response.decisions}
            for index, (article, candidate) in enumerate(batch):
                decision = by_index.get(index)
                if decision is None:
                    state.stats.add("adjudication_missing")
                    continue
                kind = ClusterDecisionKind(decision.decision.value)
                decisions[(article.id, candidate.id)] = _Decision(
                    kind=kind,
                    confidence=decision.confidence,
                )
                state.stats.add(f"decision_{kind.value.lower()}")

    async def _attach(
        self,
        ctx: JobContext,
        session: AsyncSession,
        article: AssignableArticle,
        candidate: EventCandidate,
        score: PairScore,
        *,
        method: AssignmentMethod,
        state: _RunState,
        confidence: float | None = None,
    ) -> None:
        membership = EventMembershipService(session)
        await membership.add_member(
            event_id=candidate.id,
            article_id=article.id,
            method=method,
            confidence=(
                confidence
                if confidence is not None and confidence > 0.0
                else score.score
            ),
            score_breakdown={
                "band": score.band,
                **score.components,
            },
            assigned_at=state.now,
        )
        aggregate = await membership.recompute(candidate.id)
        await membership.reactivate(candidate.id)

        event = await session.get(Event, candidate.id)
        if event is not None:
            event.latest_published_at = aggregate.latest_published_at
            event.last_updated_at = state.now
            if (
                article.published_at is not None
                and article.published_at < event.first_reported_at
            ):
                event.first_reported_at = article.published_at
            event.locations = _merge_locations(event.locations, article.locations)
            if event.country_code is None:
                event.country_code = EventAssignmentService.article_country(article)
            if event.location_name is None and event.locations:
                primary = event.locations[0]
                name = primary.get("name")
                if isinstance(name, str) and name.strip():
                    event.location_name = name.strip()[:255]
                    code = primary.get("country_code")
                    if isinstance(code, str) and len(code) == 2:
                        event.country_code = code.upper()
            if event.location is None and event.location_name:
                geocoded = await ctx.require_geocoder().geocode(
                    event.location_name,
                    country_code=event.country_code,
                )
                if geocoded is not None:
                    event.location = (
                        f"SRID=4326;POINT({geocoded.longitude} {geocoded.latitude})"
                    )
            # Membership changed, so the description is stale.
            event.member_hash = None

        await ArticleAnalysisService(session).finalize(
            article.id,
            status=IngestStatus.CLUSTERED,
        )
        state.stats.add(
            "attached_auto" if method == AssignmentMethod.AUTO else "attached_llm"
        )

    async def _create(
        self,
        ctx: JobContext,
        session: AsyncSession,
        article: AssignableArticle,
        state: _RunState,
    ) -> None:
        assignment = EventAssignmentService(session)
        location_name, country_code = _primary_location(article)
        latitude: float | None = None
        longitude: float | None = None
        if location_name:
            geocoded = await ctx.require_geocoder().geocode(
                location_name,
                country_code=country_code,
            )
            if geocoded is not None:
                latitude = geocoded.latitude
                longitude = geocoded.longitude

        category = article.category.value
        color = PREDEFINED_CATEGORIES.get(category, {}).get(
            "color",
            DEFAULT_CATEGORY_COLOR,
        )
        first_reported_at = article.published_at or state.now
        event = await assignment.create_event(
            article,
            headline=_headline(article),
            summary=article.fact,
            category=category,
            category_color=color,
            impact_level=_impact_level(article.severity),
            scope=article.scope or EventScope.COUNTRY,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            country_code=country_code,
            first_reported_at=first_reported_at,
            latest_published_at=article.published_at,
            now=state.now,
        )
        membership = EventMembershipService(session)
        await membership.add_member(
            event_id=event.id,
            article_id=article.id,
            method=AssignmentMethod.AUTO,
            confidence=1.0,
            score_breakdown={"band": "new_event"},
            assigned_at=state.now,
        )
        await membership.recompute(event.id)
        await ArticleAnalysisService(session).finalize(
            article.id,
            status=IngestStatus.CLUSTERED,
        )
        state.stats.add("events_created")


def _find_candidate(
    pending: Sequence[_PendingArticle],
    candidate_id: uuid.UUID,
) -> EventCandidate | None:
    for item in pending:
        for candidate, _score in item.candidates:
            if candidate.id == candidate_id:
                return candidate
    return None


def _pair_hash(
    article_id: uuid.UUID,
    candidate: EventCandidate,
    prompt_version: str,
) -> str:
    payload = "|".join(
        [
            "cluster",
            str(article_id),
            str(candidate.id),
            candidate.member_hash or "none",
            prompt_version,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _headline(article: AssignableArticle) -> str:
    text = " ".join(article.fact.split())
    if len(text) <= 120:
        return text
    return text[:117].rstrip() + "..."


def _impact_level(severity: int | None) -> ImpactLevel:
    if severity is None:
        return ImpactLevel.MODERATE
    if severity >= 5:
        return ImpactLevel.CRITICAL
    if severity == 4:
        return ImpactLevel.MAJOR
    if severity == 3:
        return ImpactLevel.MODERATE
    return ImpactLevel.MINOR


def _article_location(article: AssignableArticle) -> GeoLocation | None:
    place = _article_place(article)
    if place is None:
        return None
    return GeoLocation(name=place[0], country_code=place[1])


def _primary_location(article: AssignableArticle) -> tuple[str | None, str | None]:
    place = _article_place(article)
    if place is None:
        return None, None
    return place


def _article_place(article: AssignableArticle) -> tuple[str, str | None] | None:
    for location in article.locations:
        name = location.get("name")
        if isinstance(name, str) and name.strip():
            code = location.get("country_code")
            return (
                name.strip(),
                code.upper() if isinstance(code, str) and len(code) == 2 else None,
            )
    for entity in article.entities:
        if str(entity.get("kind", "")).strip().upper() != "LOCATION":
            continue
        name = entity.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip(), None
    return None


def _merge_locations(
    existing: Sequence[dict[str, object]],
    incoming: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[str] = set()
    for location in [*existing, *incoming]:
        name = location.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        key = name.strip().casefold()
        if key in seen:
            continue
        seen.add(key)
        code = location.get("country_code")
        merged.append(
            {
                "name": name.strip(),
                "country_code": (
                    code.upper() if isinstance(code, str) and len(code) == 2 else None
                ),
            }
        )
        if len(merged) == 3:
            break
    return merged


def _article_side(article: AssignableArticle) -> PairSide:
    location_name, _country = _primary_location(article)
    entities = [
        name.strip()
        for entity in article.entities
        if isinstance((name := entity.get("name")), str) and name.strip()
    ]
    occurred_at = article.effective_time
    return PairSide(
        headline=article.title[:500],
        fact=article.fact[:400],
        summary=(article.feed_summary or "")[:1_500] or None,
        entities=entities[:8],
        location=location_name,
        occurred_at=occurred_at.isoformat() if occurred_at is not None else None,
        category=article.category.value,
    )


def _event_side(candidate: EventCandidate) -> PairSide:
    location_name: str | None = None
    for location in candidate.locations:
        name = location.get("name")
        if isinstance(name, str) and name.strip():
            location_name = name.strip()
            break
    occurred_at = candidate.event_time or candidate.latest_published_at
    return PairSide(
        headline=candidate.ai_headline[:500],
        fact=(candidate.ai_summary or "")[:400] or None,
        summary=candidate.ai_summary,
        entities=sorted(candidate.entities)[:8],
        location=location_name,
        occurred_at=occurred_at.isoformat() if occurred_at is not None else None,
        category=candidate.category,
    )
