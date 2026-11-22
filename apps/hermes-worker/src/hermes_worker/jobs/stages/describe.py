from __future__ import annotations
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hermes_ai import (
    DescribeEventInput,
    DescribeMemberFact,
    EventDescription,
)
from hermes_db.enums import EventScope, EventStatus, ImpactLevel
from hermes_db.models.event import Event
from hermes_db.services import (
    EventMembershipService,
    MemberRecord,
    member_hash,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_worker.jobs.context import (
    BudgetExhaustedError,
    JobContext,
    StageName,
    StageStats,
)


logger = logging.getLogger(__name__)

MAX_LOCATIONS = 3
MAX_HEADLINE_CHARS = 120
MAX_SUMMARY_CHARS = 900


@dataclass(frozen=True, slots=True)
class _EventFacts:
    event: Event
    members: tuple[MemberRecord, ...]
    hash: str


class DescribeStage:
    """Synthesize one description per event from its independent family facts."""

    name = StageName.DESCRIBE

    async def run(self, ctx: JobContext) -> StageStats:
        stats = StageStats()
        if ctx.budget.remaining_llm_calls <= 0:
            stats.add("budget_empty")
            return stats

        async with ctx.session_factory() as session:
            event_ids = list(
                (
                    await session.execute(
                        select(Event.id)
                        .where(
                            Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE])
                        )
                        .where(Event.merged_into_id.is_(None))
                        .where(Event.member_hash.is_(None))
                        .order_by(Event.importance_score.desc())
                        .limit(ctx.settings.EVENT_DESCRIBE_BATCH_SIZE)
                    )
                )
                .scalars()
                .all()
            )
        stats.add("candidates", len(event_ids))
        if not event_ids:
            return stats

        async with ctx.session_factory() as session:
            facts = await _load_facts(session, event_ids)
        stats.add("loaded", len(facts))
        if not facts:
            return stats

        try:
            ctx.budget.reserve_llm_calls(1)
        except BudgetExhaustedError:
            stats.add("budget_exhausted")
            return stats
        stats.add("describe_calls")
        describer = ctx.require_ai().describer
        inputs = [_describe_input(index, item) for index, item in enumerate(facts)]
        response = await describer.describe(inputs)
        by_index = (
            {description.index: description for description in response.descriptions}
            if response is not None
            else {}
        )

        now = datetime.now(UTC)
        async with ctx.session_factory() as session:
            for index, item in enumerate(facts):
                event = await session.get(Event, item.event.id)
                if event is None:
                    continue
                previous_location = event.location_name
                description = by_index.get(index)
                if description is None:
                    _apply_fallback(event, item)
                    stats.add("described_fallback")
                else:
                    _apply_description(event, description)
                    stats.add("described_llm")
                if event.location_name != previous_location:
                    await _geocode_primary(ctx, event, stats)
                event.member_hash = item.hash
                event.version += 1
                event.last_updated_at = now
            await session.commit()

        return stats


async def _load_facts(
    session: AsyncSession,
    event_ids: Sequence[uuid.UUID],
) -> list[_EventFacts]:
    membership = EventMembershipService(session)
    members = await membership.current_members(event_ids)
    by_event: dict[uuid.UUID, list[MemberRecord]] = {}
    for member in members:
        by_event.setdefault(member.event_id, []).append(member)

    events = list(
        (
            await session.execute(
                select(Event)
                .where(Event.id.in_(event_ids))
                .order_by(Event.importance_score.desc())
            )
        )
        .scalars()
        .all()
    )
    facts: list[_EventFacts] = []
    for event in events:
        event_members = [
            member
            for member in _one_per_family(by_event.get(event.id, []))
            if member.fact
        ]
        if not event_members:
            continue
        facts.append(
            _EventFacts(
                event=event,
                members=tuple(event_members),
                hash=member_hash([member.article_id for member in event_members]),
            )
        )
    return facts


def _one_per_family(members: Sequence[MemberRecord]) -> list[MemberRecord]:
    """Keep the earliest member of each syndication family."""
    seen: set[uuid.UUID] = set()
    selected: list[MemberRecord] = []
    ordered = sorted(
        members,
        key=lambda member: (
            member.published_at is None,
            member.published_at or datetime.min.replace(tzinfo=UTC),
            member.article_id,
        ),
    )
    for member in ordered:
        key = member.family_id or member.article_id
        if key in seen:
            continue
        seen.add(key)
        selected.append(member)
    return selected


def _describe_input(index: int, item: _EventFacts) -> DescribeEventInput:
    return DescribeEventInput(
        index=index,
        category=item.event.category,
        facts=[
            DescribeMemberFact(
                fact=member.fact or "",
                source=(member.source_name or "unknown")[:120],
                published_at=(
                    member.published_at.isoformat()
                    if member.published_at is not None
                    else None
                ),
                entities=[
                    name.strip()
                    for entity in member.entities
                    if isinstance((name := entity.get("name")), str) and name.strip()
                ][:8],
                locations=[
                    name.strip()
                    for location in member.locations
                    if isinstance((name := location.get("name")), str) and name.strip()
                ][:3],
                scale_facts={
                    key: value
                    for key, value in member.scale_facts
                    if isinstance(value, (str, int, float, bool))
                },
            )
            for member in item.members[:8]
        ],
    )


def _apply_description(event: Event, description: EventDescription) -> None:
    event.ai_headline = description.headline[:MAX_HEADLINE_CHARS]
    event.ai_summary = description.summary[:MAX_SUMMARY_CHARS]
    event.impact_level = ImpactLevel(description.impact_level.value)
    event.scope = EventScope(description.scope.value)
    locations = [
        {
            "name": location.name[:255],
            "country_code": (
                location.country_code.upper()
                if location.country_code is not None
                else None
            ),
        }
        for location in description.locations[:MAX_LOCATIONS]
    ]
    event.locations = locations
    if locations:
        name = locations[0]["name"]
        if isinstance(name, str):
            event.location_name = name
        code = locations[0]["country_code"]
        if isinstance(code, str) and len(code) == 2:
            event.country_code = code


def _apply_fallback(event: Event, item: _EventFacts) -> None:
    facts = [member.fact for member in item.members if member.fact]
    headline = " ".join((facts[0] if facts else event.ai_headline).split())
    if len(headline) > MAX_HEADLINE_CHARS:
        headline = headline[: MAX_HEADLINE_CHARS - 3].rstrip() + "..."
    event.ai_headline = headline
    if facts:
        event.ai_summary = " ".join(facts[:2])[:MAX_SUMMARY_CHARS]
    locations = _member_locations(item.members)
    if locations:
        event.locations = locations
        name = locations[0]["name"]
        if isinstance(name, str):
            event.location_name = name
        code = locations[0]["country_code"]
        if isinstance(code, str) and len(code) == 2:
            event.country_code = code


async def _geocode_primary(
    ctx: JobContext,
    event: Event,
    stats: StageStats,
) -> None:
    """Resolve the description's primary location through the shared geocoder."""
    if not event.location_name:
        event.location = None
        return
    geocoded = await ctx.require_geocoder().geocode(event.location_name)
    if geocoded is None:
        # Never leave a pin on the previous location after the name changed.
        event.location = None
        stats.add("geocode_miss")
        return
    event.location = f"SRID=4326;POINT({geocoded.longitude} {geocoded.latitude})"
    stats.add("geocoded")


def _member_locations(
    members: Sequence[MemberRecord],
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[str] = set()
    for member in members:
        for location in member.locations:
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
                    "name": name.strip()[:255],
                    "country_code": (
                        code.upper()
                        if isinstance(code, str) and len(code) == 2
                        else None
                    ),
                }
            )
            if len(merged) == MAX_LOCATIONS:
                return merged
    return merged
