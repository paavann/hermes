from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import (
    ArticleType,
    CredibilityTier,
    EventStatus,
    ImpactLevel,
    SelectionTier,
    VerificationStatus,
)
from hermes_db.models.event import Event
from hermes_db.services.event_membership import EventMembershipService, MemberRecord
from hermes_db.utils.datetime import ensure_utc


SCORE_VERSION = "score-v2"
STRENGTH_WEIGHT = 0.40
IMPACT_WEIGHT = 0.30
VERIFY_WEIGHT = 0.15
QUALITY_WEIGHT = 0.15

SCORING_CREDIBILITY: dict[CredibilityTier, float] = {
    CredibilityTier.TIER_1: 3.0,
    CredibilityTier.TIER_2: 2.0,
    CredibilityTier.TIER_3: 1.0,
    CredibilityTier.TIER_4: 1.0,
}
IMPACT_VALUE: dict[ImpactLevel, float] = {
    ImpactLevel.CRITICAL: 1.0,
    ImpactLevel.MAJOR: 0.8,
    ImpactLevel.MODERATE: 0.55,
    ImpactLevel.MINOR: 0.3,
}
VERIFY_VALUE: dict[VerificationStatus, float] = {
    VerificationStatus.CONFIRMED: 1.0,
    VerificationStatus.CORROBORATED: 0.85,
    VerificationStatus.SINGLE_SOURCE: 0.75,
    VerificationStatus.CONFLICTING: 0.5,
    VerificationStatus.UNVERIFIED: 0.0,
}
HALF_LIFE_CRITICAL_HOURS = 18.0
HALF_LIFE_MAJOR_HOURS = 36.0
HALF_LIFE_DEFAULT_HOURS = 96.0

PRIMARY_THRESHOLD = 50.0
FILLER_THRESHOLD = 22.0
HYSTERESIS = 5.0
SINGLE_SOURCE_CAP = 65.0
BREAKING_MAX_AGE_HOURS = 2.0
BREAKING_MIN_SCORE = 35.0


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: float
    base: float
    strength: float
    impact: float
    verify: float
    quality: float
    freshness: float
    age_hours: float
    half_life_hours: float
    capped: bool
    breaking_override: bool
    breakdown: dict[str, object]


def _component(value: float, weight: float) -> dict[str, object]:
    return {
        "value": round(value, 4),
        "weight": weight,
        "contribution": round(value * weight, 4),
    }


def _family_credibility(members: Sequence[MemberRecord]) -> list[float]:
    best: dict[str, float] = {}
    for member in members:
        key = (
            f"family:{member.family_id}"
            if member.family_id is not None
            else f"article:{member.article_id}"
        )
        value = SCORING_CREDIBILITY.get(
            member.source_credibility or CredibilityTier.TIER_4,
            SCORING_CREDIBILITY[CredibilityTier.TIER_4],
        )
        current = best.get(key)
        if current is None or value > current:
            best[key] = value
    return list(best.values())


def _quality(members: Sequence[MemberRecord]) -> float:
    specificity = max((member.specificity or 3) for member in members)
    consequence = max((member.consequence or 3) for member in members)
    raw = 1.0 - 0.15 * (5 - specificity) - 0.10 * (5 - consequence)
    return min(1.0, max(0.5, raw))


def _age_hours(
    *,
    latest_published_at: datetime | None,
    event_time: datetime | None,
    now: datetime,
) -> float:
    anchor = latest_published_at or event_time
    if anchor is None:
        return 0.0
    delta = ensure_utc(now) - ensure_utc(anchor)
    return max(0.0, delta.total_seconds() / 3600.0)


def _half_life(impact: ImpactLevel) -> float:
    if impact == ImpactLevel.CRITICAL:
        return HALF_LIFE_CRITICAL_HOURS
    if impact == ImpactLevel.MAJOR:
        return HALF_LIFE_MAJOR_HOURS
    return HALF_LIFE_DEFAULT_HOURS


def compute_score(
    *,
    members: Sequence[MemberRecord],
    impact: ImpactLevel,
    verification: VerificationStatus,
    latest_published_at: datetime | None,
    event_time: datetime | None,
    now: datetime,
) -> ScoreResult:
    """Compute the single explainable importance score.

    The formula is deliberately deterministic: an event's score is a pure
    function of its current members, impact, verification, and age.
    """
    if not members:
        return ScoreResult(
            score=0.0,
            base=0.0,
            strength=0.0,
            impact=IMPACT_VALUE.get(impact, 0.0),
            verify=VERIFY_VALUE.get(verification, 0.0),
            quality=0.5,
            freshness=0.0,
            age_hours=0.0,
            half_life_hours=_half_life(impact),
            capped=False,
            breaking_override=False,
            breakdown={
                "version": SCORE_VERSION,
                "score": 0.0,
                "base": 0.0,
                "reason": "no_members",
            },
        )

    family_values = _family_credibility(members)
    strength = min(1.0, sum(family_values) / 9.0)
    impact_value = IMPACT_VALUE.get(impact, 0.0)
    verify_value = VERIFY_VALUE.get(verification, 0.0)
    quality = _quality(members)
    base = 100.0 * (
        STRENGTH_WEIGHT * strength
        + IMPACT_WEIGHT * impact_value
        + VERIFY_WEIGHT * verify_value
        + QUALITY_WEIGHT * quality
    )

    age_hours = _age_hours(
        latest_published_at=latest_published_at,
        event_time=event_time,
        now=now,
    )
    half_life = _half_life(impact)
    freshness = math.exp(-age_hours / half_life)
    score = base * freshness

    capped = False
    if verification == VerificationStatus.SINGLE_SOURCE and score > SINGLE_SOURCE_CAP:
        score = SINGLE_SOURCE_CAP
        capped = True

    breaking = (
        age_hours <= BREAKING_MAX_AGE_HOURS
        and impact in {ImpactLevel.CRITICAL, ImpactLevel.MAJOR}
        and any(member.article_type == ArticleType.BREAKING for member in members)
        and score >= BREAKING_MIN_SCORE
    )

    score = round(score, 2)
    breakdown: dict[str, object] = {
        "version": SCORE_VERSION,
        "score": score,
        "base": round(base, 4),
        "strength": _component(strength, STRENGTH_WEIGHT),
        "impact": _component(impact_value, IMPACT_WEIGHT),
        "verify": _component(verify_value, VERIFY_WEIGHT),
        "quality": _component(quality, QUALITY_WEIGHT),
        "age_hours": round(age_hours, 3),
        "half_life_hours": half_life,
        "freshness": round(freshness, 4),
        "capped": capped,
        "breaking_override": breaking,
        "family_count": len(family_values),
    }
    return ScoreResult(
        score=score,
        base=round(base, 4),
        strength=strength,
        impact=impact_value,
        verify=verify_value,
        quality=quality,
        freshness=freshness,
        age_hours=age_hours,
        half_life_hours=half_life,
        capped=capped,
        breaking_override=breaking,
        breakdown=breakdown,
    )


def select_tier(
    score: float,
    *,
    previous: SelectionTier | None,
    breaking_override: bool = False,
) -> tuple[SelectionTier, str]:
    """Map a score to a tier, demoting only outside a +/-5 band."""
    if breaking_override:
        return SelectionTier.PRIMARY, "breaking_override"

    if previous == SelectionTier.PRIMARY:
        if score >= PRIMARY_THRESHOLD - HYSTERESIS:
            return SelectionTier.PRIMARY, "primary_held"
        if score >= FILLER_THRESHOLD - HYSTERESIS:
            return SelectionTier.FILLER, "demoted_from_primary"
        return SelectionTier.DROP, "dropped_from_primary"

    if previous == SelectionTier.FILLER:
        if score >= PRIMARY_THRESHOLD:
            return SelectionTier.PRIMARY, "promoted_to_primary"
        if score >= FILLER_THRESHOLD - HYSTERESIS:
            return SelectionTier.FILLER, "filler_held"
        return SelectionTier.DROP, "dropped_from_filler"

    if previous == SelectionTier.DROP:
        if score >= PRIMARY_THRESHOLD:
            return SelectionTier.PRIMARY, "promoted_to_primary"
        if score >= FILLER_THRESHOLD + HYSTERESIS:
            return SelectionTier.FILLER, "promoted_to_filler"
        return SelectionTier.DROP, "drop_held"

    if score >= PRIMARY_THRESHOLD:
        return SelectionTier.PRIMARY, "initial_primary"
    if score >= FILLER_THRESHOLD:
        return SelectionTier.FILLER, "initial_filler"
    return SelectionTier.DROP, "initial_drop"


@dataclass(frozen=True, slots=True)
class EventScoreState:
    id: uuid.UUID
    impact_level: ImpactLevel
    verification_status: VerificationStatus
    latest_published_at: datetime | None
    event_time: datetime | None
    selection_tier: SelectionTier


class EventScoringService:
    """Reads active events in pages and persists score/tier fields."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_states(
        self,
        *,
        after_id: uuid.UUID | None = None,
        limit: int = 500,
    ) -> list[EventScoreState]:
        stmt = (
            select(
                Event.id,
                Event.impact_level,
                Event.verification_status,
                Event.latest_published_at,
                Event.event_time,
                Event.selection_tier,
            )
            .where(Event.status == EventStatus.ACTIVE)
            .order_by(Event.id)
            .limit(limit)
        )
        if after_id is not None:
            stmt = stmt.where(Event.id > after_id)
        rows = (await self._session.execute(stmt)).all()
        return [
            EventScoreState(
                id=row.id,
                impact_level=row.impact_level,
                verification_status=row.verification_status,
                latest_published_at=(
                    ensure_utc(row.latest_published_at)
                    if row.latest_published_at is not None
                    else None
                ),
                event_time=(
                    ensure_utc(row.event_time)
                    if row.event_time is not None
                    else None
                ),
                selection_tier=row.selection_tier,
            )
            for row in rows
        ]

    async def rescore(
        self,
        event_id: uuid.UUID,
        *,
        now: datetime,
    ) -> ScoreResult | None:
        """Recompute and persist one event from its current members."""
        event = await self._session.get(Event, event_id)
        if event is None:
            return None
        members = await EventMembershipService(
            self._session
        ).current_members([event_id])
        result = compute_score(
            members=members,
            impact=event.impact_level,
            verification=event.verification_status,
            latest_published_at=event.latest_published_at,
            event_time=event.event_time,
            now=now,
        )
        tier, reason = select_tier(
            result.score,
            previous=event.selection_tier,
            breaking_override=result.breaking_override,
        )
        await self.apply(
            event_id,
            result=result,
            tier=tier,
            reason=reason,
            now=now,
        )
        return result

    async def apply(
        self,
        event_id: uuid.UUID,
        *,
        result: ScoreResult,
        tier: SelectionTier,
        reason: str,
        now: datetime,
    ) -> None:
        await self._session.execute(
            update(Event)
            .where(Event.id == event_id)
            .values(
                importance_score=result.score,
                score_breakdown=result.breakdown,
                score_version=SCORE_VERSION,
                scored_at=now,
                selection_tier=tier,
                selection_reason=reason,
                selected_at=now,
            )
            .execution_options(synchronize_session=False)
        )

