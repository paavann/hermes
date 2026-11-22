from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import EventStatus, EventTlStatus
from hermes_db.models.article import Article
from hermes_db.models.event import Event
from hermes_db.models.event_member import EventMember
from hermes_db.models.event_tl import EventTl
from hermes_db.services.event_membership import EventMembershipService
from hermes_db.utils.datetime import ensure_utc


@dataclass(frozen=True, slots=True)
class EventPairState:
    id: uuid.UUID
    ai_headline: str
    ai_summary: str | None
    category: str
    event_time: datetime | None
    latest_published_at: datetime | None
    first_reported_at: datetime
    country_code: str | None
    location_name: str | None
    latitude: float | None
    longitude: float | None
    embedding: tuple[float, ...] | None
    embedding_model: str | None
    member_hash: str | None
    article_count: int
    thread_id: uuid.UUID | None
    status: EventStatus


class EventMergeService:
    """Merges duplicate events by reassigning membership, never by deleting."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._membership = EventMembershipService(session)

    async def resolve_event_id(self, event_id: uuid.UUID) -> uuid.UUID:
        current = event_id
        seen: set[uuid.UUID] = set()
        while current not in seen:
            seen.add(current)
            target = await self._session.scalar(
                select(Event.merged_into_id).where(Event.id == current)
            )
            if target is None:
                return current
            current = target
        return current

    async def recent_states(
        self,
        *,
        since: datetime,
        limit: int = 200,
    ) -> list[EventPairState]:
        stmt = (
            select(
                Event.id,
                Event.ai_headline,
                Event.ai_summary,
                Event.category,
                Event.event_time,
                Event.latest_published_at,
                Event.first_reported_at,
                Event.country_code,
                Event.location_name,
                ST_Y(Event.location).label("latitude"),
                ST_X(Event.location).label("longitude"),
                Event.embedding,
                Event.embedding_model,
                Event.member_hash,
                Event.article_count,
                Event.thread_id,
                Event.status,
            )
            .where(Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
            .where(Event.merged_into_id.is_(None))
            .where(Event.last_updated_at >= since)
            .order_by(Event.importance_score.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        states: list[EventPairState] = []
        for row in rows:
            embedding: tuple[float, ...] | None = None
            if row.embedding is not None:
                embedding = tuple(float(value) for value in row.embedding)
            states.append(
                EventPairState(
                    id=row.id,
                    ai_headline=row.ai_headline,
                    ai_summary=row.ai_summary,
                    category=row.category,
                    event_time=(
                        ensure_utc(row.event_time)
                        if row.event_time is not None
                        else None
                    ),
                    latest_published_at=(
                        ensure_utc(row.latest_published_at)
                        if row.latest_published_at is not None
                        else None
                    ),
                    first_reported_at=ensure_utc(row.first_reported_at),
                    country_code=row.country_code,
                    location_name=row.location_name,
                    latitude=float(row.latitude) if row.latitude is not None else None,
                    longitude=float(row.longitude)
                    if row.longitude is not None
                    else None,
                    embedding=embedding,
                    embedding_model=row.embedding_model,
                    member_hash=row.member_hash,
                    article_count=row.article_count,
                    thread_id=row.thread_id,
                    status=row.status,
                )
            )
        return states

    async def family_sets(
        self,
        event_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, frozenset[uuid.UUID]]:
        """Load each event's current syndication family ids."""
        if not event_ids:
            return {}
        stmt = (
            select(EventMember.event_id, Article.family_id)
            .join(Article, Article.id == EventMember.article_id)
            .where(EventMember.event_id.in_(event_ids))
            .where(EventMember.is_current.is_(True))
            .where(Article.family_id.is_not(None))
        )
        grouped: dict[uuid.UUID, set[uuid.UUID]] = {
            event_id: set() for event_id in event_ids
        }
        for event_id, family_id in (await self._session.execute(stmt)).all():
            grouped[event_id].add(family_id)
        return {
            event_id: frozenset(families)
            for event_id, families in grouped.items()
        }

    async def candidate_entities(
        self,
        event_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, set[str]]:
        members = await self._membership.current_members(event_ids)
        grouped: dict[uuid.UUID, set[str]] = {event_id: set() for event_id in event_ids}
        for member in members:
            for entity in member.entities:
                name = entity.get("name")
                if isinstance(name, str) and name.strip():
                    grouped[member.event_id].add(name.strip().casefold())
        return grouped

    async def merge(
        self,
        *,
        survivor_id: uuid.UUID,
        loser_id: uuid.UUID,
        reason: str,
        now: datetime | None = None,
    ) -> bool:
        """Move loser members to survivor and redirect the loser.

        Returns False when the merge is already in effect, which makes the
        reconcile stage safe to retry.
        """
        if survivor_id == loser_id:
            return False
        moment = now or datetime.now(UTC)
        survivor_id = await self.resolve_event_id(survivor_id)
        loser_id = await self.resolve_event_id(loser_id)
        if survivor_id == loser_id:
            return False

        loser = await self._session.get(Event, loser_id)
        survivor = await self._session.get(Event, survivor_id)
        if loser is None or survivor is None:
            return False
        if loser.merged_into_id == survivor_id:
            return False
        if loser.status == EventStatus.MERGED:
            return False

        await self._session.execute(
            update(EventMember)
            .where(EventMember.event_id == loser_id)
            .where(EventMember.is_current.is_(True))
            .values(event_id=survivor_id)
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(
            update(Article)
            .where(Article.event_id == loser_id)
            .values(event_id=survivor_id)
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(
            update(EventTl)
            .where(EventTl.event_id == loser_id)
            .values(
                status=EventTlStatus.FAILED,
                nodes=[],
                edges=[],
                tl_summary="",
                event_version=None,
                generated_at=moment,
            )
            .execution_options(synchronize_session=False)
        )

        if survivor.thread_id is None and loser.thread_id is not None:
            survivor.thread_id = loser.thread_id

        loser.status = EventStatus.MERGED
        loser.merged_into_id = survivor_id
        loser.merged_at = moment
        loser.merge_reason = reason[:500]
        loser.thread_id = None
        loser.version += 1

        await self._session.flush()
        await self._membership.recompute(loser_id)
        aggregate = await self._membership.recompute(survivor_id)
        # The member set changed, so the description is stale. Clearing the
        # hash makes the next describe run rebuild it.
        survivor.member_hash = None
        survivor.latest_published_at = aggregate.latest_published_at
        survivor.version += 1
        survivor.last_updated_at = moment
        return True
