from __future__ import annotations
import asyncio
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hermes_ai import (
    DescribeEventInput,
    DescribeExtractor,
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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_worker.jobs.context import (
    JobContext,
    StageName,
    StageStats,
)


logger = logging.getLogger(__name__)

MAX_LOCATIONS = 3
MAX_HEADLINE_CHARS = 120
MAX_SUMMARY_CHARS = 900
MAX_DESCRIBE_ROUNDS = 20
DESCRIBE_CONCURRENCY = 5
DESCRIBE_WINDOW_MULTIPLIER = 4
_GEOCODE_LOCK = asyncio.Lock()


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
        processed: set[uuid.UUID] = set()
        rounds = 0
        batch_size = ctx.settings.EVENT_DESCRIBE_BATCH_SIZE
        selection_limit = batch_size * DESCRIBE_CONCURRENCY * DESCRIBE_WINDOW_MULTIPLIER
        semaphore = asyncio.Semaphore(DESCRIBE_CONCURRENCY)

        while rounds < MAX_DESCRIBE_ROUNDS:
            if ctx.budget.remaining_llm_calls <= 0:
                stats.add("budget_exhausted")
                break

            event_ids = await _candidate_ids(
                ctx,
                exclude=processed,
                limit=min(selection_limit, ctx.budget.remaining_llm_calls * batch_size),
            )
            stats.add("candidates", len(event_ids))
            if not event_ids:
                break

            processed.update(event_ids)
            rounds += 1

            async with ctx.session_factory() as session:
                facts = await _load_facts(session, event_ids)
            stats.add("loaded", len(facts))
            if not facts:
                continue

            batches = [
                facts[offset : offset + batch_size]
                for offset in range(0, len(facts), batch_size)
            ]
            available = min(len(batches), ctx.budget.remaining_llm_calls)
            if available < len(batches):
                stats.add("budget_exhausted")
                batches = batches[:available]
            if not batches:
                break

            ctx.budget.reserve_llm_calls(len(batches))
            stats.add("describe_calls", len(batches))
            describer = ctx.require_ai().describer
            await asyncio.gather(
                *(
                    self._run_limited_batch(
                        semaphore, ctx, describer, batch, stats
                    )
                    for batch in batches
                )
            )

        if rounds >= MAX_DESCRIBE_ROUNDS:
            stats.add("max_rounds")
        stats.add("pending_remaining", await _pending_count(ctx))
        return stats

    async def _run_limited_batch(
        self,
        semaphore: asyncio.Semaphore,
        ctx: JobContext,
        describer: DescribeExtractor,
        batch: Sequence[_EventFacts],
        stats: StageStats,
    ) -> None:
        async with semaphore:
            await self._describe_batch(ctx, describer, batch, stats)

    @staticmethod
    async def _describe_batch(
        ctx: JobContext,
        describer: DescribeExtractor,
        facts: Sequence[_EventFacts],
        stats: StageStats,
    ) -> None:
        inputs = [_describe_input(index, item) for index, item in enumerate(facts)]
        response = await describer.describe(inputs)
        if response is None:
            stats.add("describe_failed")
            return

        by_index = {
            description.index: description
            for description in response.descriptions
        }
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
                    _apply_description(event, description, item.members)
                    stats.add("described_llm")
                if event.location_name and (
                    description is not None
                    or event.location_name != previous_location
                    or event.location is None
                ):
                    geocoded = await _geocode_event(ctx, event, stats)
                    if not geocoded and (
                        description is not None
                        or event.location_name != previous_location
                    ):
                        event.location = None
                event.member_hash = item.hash
                event.version += 1
                event.last_updated_at = now
            await session.commit()


async def _candidate_ids(
    ctx: JobContext,
    *,
    exclude: set[uuid.UUID],
    limit: int,
) -> list[uuid.UUID]:
    stmt = (
        select(Event.id)
        .where(Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
        .where(Event.merged_into_id.is_(None))
        .where(Event.member_hash.is_(None))
        .order_by(
            Event.event_time.desc().nulls_last(),
            Event.latest_published_at.desc().nulls_last(),
            Event.first_reported_at.desc(),
        )
        .limit(limit)
    )
    if exclude:
        stmt = stmt.where(Event.id.notin_(exclude))
    async with ctx.session_factory() as session:
        return list((await session.execute(stmt)).scalars().all())


async def _pending_count(ctx: JobContext) -> int:
    async with ctx.session_factory() as session:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(Event)
                .where(Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
                .where(Event.merged_into_id.is_(None))
                .where(Event.member_hash.is_(None))
            )
            or 0
        )


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


def _apply_description(
    event: Event,
    description: EventDescription,
    members: Sequence[MemberRecord],
) -> None:
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
        if location.name.strip()
    ]
    if not locations:
        locations = _member_locations(members)
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


async def _geocode_event(
    ctx: JobContext,
    event: Event,
    stats: StageStats,
) -> bool:
    """Resolve the first locatable candidate through the shared geocoder."""
    candidates: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for location in event.locations:
        name = location.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        key = name.strip().casefold()
        if key in seen:
            continue
        seen.add(key)
        code = location.get("country_code")
        candidates.append(
            (
                name.strip(),
                code.upper() if isinstance(code, str) and len(code) == 2 else None,
            )
        )
    if event.location_name:
        key = event.location_name.strip().casefold()
        if key and key not in seen:
            candidates.insert(0, (event.location_name.strip(), event.country_code))

    geocoder = ctx.require_geocoder()
    for name, code in candidates[:MAX_LOCATIONS]:
        effective = code or event.country_code
        # The geocoder shares one cache session, so serialize cache access.
        async with _GEOCODE_LOCK:
            geocoded = await geocoder.geocode(name, country_code=effective)
        if geocoded is None:
            stats.add("geocode_miss")
            continue
        event.location = f"SRID=4326;POINT({geocoded.longitude} {geocoded.latitude})"
        event.location_name = name[:255]
        if effective is not None:
            event.country_code = effective
        stats.add("geocoded")
        return True
    return False


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
