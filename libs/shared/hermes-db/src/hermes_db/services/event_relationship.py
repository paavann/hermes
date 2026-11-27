from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol, cast

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from hermes_db.enums import EventRelationshipType, EventStatus, SelectionTier
from hermes_db.models.event import Event
from hermes_db.models.event_relationship import EventRelationship
from hermes_db.services.event_membership import EventMembershipService, MemberRecord
from hermes_db.utils.datetime import ensure_utc


RelationshipDirection = Literal["OUTGOING", "INCOMING"]


@dataclass(frozen=True, slots=True)
class RelationshipAnchorEvent:
    """Snapshot of an active event evaluated for pairwise relationships."""

    id: uuid.UUID
    ai_headline: str
    ai_summary: str | None
    category: str
    country_code: str | None
    location_name: str | None
    latitude: float | None
    longitude: float | None
    event_time: datetime | None
    latest_published_at: datetime | None
    first_reported_at: datetime
    importance_score: float
    member_hash: str | None
    version: int
    embedding: tuple[float, ...] | None
    embedding_model: str | None
    entities: frozenset[str]
    actors: tuple[dict[str, object], ...] = field(default=(), compare=False)
    actor_keys: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class EventRelationshipView:
    """Connected counterpart details projected for a single event."""

    id: uuid.UUID
    relationship_type: EventRelationshipType
    direction: RelationshipDirection
    confidence: float
    rationale: str
    related_event_id: uuid.UUID
    related_headline: str
    related_category: str
    related_category_color: str
    related_location_name: str | None
    related_latitude: float | None
    related_longitude: float | None
    related_importance_score: float
    related_event_time: datetime | None


@dataclass(frozen=True, slots=True)
class MapRelationshipView:
    """Pairwise relationship edge with projected coordinates for both endpoints."""

    id: uuid.UUID
    source_event_id: uuid.UUID
    target_event_id: uuid.UUID
    source_headline: str
    source_category: str
    source_category_color: str
    source_location_name: str | None
    source_latitude: float
    source_longitude: float
    target_headline: str
    target_category: str
    target_category_color: str
    target_location_name: str | None
    target_latitude: float
    target_longitude: float
    relationship_type: EventRelationshipType
    confidence: float
    rationale: str


class _AnchorRow(Protocol):
    id: uuid.UUID
    ai_headline: str
    ai_summary: str | None
    category: str
    country_code: str | None
    location_name: str | None
    latitude: float | None
    longitude: float | None
    event_time: datetime | None
    latest_published_at: datetime | None
    first_reported_at: datetime
    importance_score: float
    member_hash: str | None
    version: int
    embedding: Sequence[float] | None
    embedding_model: str | None


def canonical_pair_key(left_id: uuid.UUID, right_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return (left_id, right_id) if left_id <= right_id else (right_id, left_id)


def _extract_entities(members: Sequence[MemberRecord]) -> frozenset[str]:
    names: set[str] = set()
    for member in members:
        for entity in member.entities:
            name = entity.get("name")
            if isinstance(name, str) and name.strip():
                names.add(" ".join(name.strip().casefold().split()))
    return frozenset(names)


def _extract_actors(
    raw_actors: object,
) -> tuple[tuple[dict[str, object], ...], frozenset[str]]:
    if not isinstance(raw_actors, (list, tuple)):
        return (), frozenset()
    actors: list[dict[str, object]] = []
    keys: set[str] = set()
    for item in raw_actors:
        if not isinstance(item, dict):
            continue
        actors.append(dict(item))
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            keys.add(" ".join(name.strip().casefold().split()))
    return tuple(actors), frozenset(keys)


def _anchor_select():
    return select(
        Event.id,
        Event.ai_headline,
        Event.ai_summary,
        Event.category,
        Event.country_code,
        Event.location_name,
        ST_Y(Event.location).label("latitude"),
        ST_X(Event.location).label("longitude"),
        Event.event_time,
        Event.latest_published_at,
        Event.first_reported_at,
        Event.importance_score,
        Event.member_hash,
        Event.version,
        Event.embedding,
        Event.embedding_model,
        Event.actors,
    )


class EventRelationshipService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._membership = EventMembershipService(session)

    async def recent_anchor_events(
        self,
        *,
        since: datetime,
        limit: int = 100,
    ) -> list[RelationshipAnchorEvent]:
        moment = ensure_utc(since)
        stmt = (
            _anchor_select()
            .where(Event.status == EventStatus.ACTIVE)
            .where(Event.merged_into_id.is_(None))
            .where(Event.selection_tier != SelectionTier.DROP)
            .where(
                func.coalesce(
                    Event.event_time,
                    Event.latest_published_at,
                    Event.first_reported_at,
                )
                >= moment
            )
            .order_by(Event.last_updated_at.desc(), Event.importance_score.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return await self._hydrate_anchors(cast(Sequence[_AnchorRow], rows))

    async def neighbor_candidates(
        self,
        anchor: RelationshipAnchorEvent,
        *,
        since: datetime,
        min_embedding_sim: float = 0.62,
        limit: int = 8,
    ) -> list[RelationshipAnchorEvent]:
        if anchor.embedding is None or anchor.embedding_model is None:
            return []
        moment = ensure_utc(since)
        max_distance = max(0.0, 1.0 - min_embedding_sim)
        distance = Event.embedding.cosine_distance(list(anchor.embedding))
        stmt = (
            _anchor_select()
            .where(Event.id != anchor.id)
            .where(Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
            .where(Event.merged_into_id.is_(None))
            .where(Event.selection_tier != SelectionTier.DROP)
            .where(Event.embedding.is_not(None))
            .where(Event.embedding_model == anchor.embedding_model)
            .where(
                func.coalesce(
                    Event.event_time,
                    Event.latest_published_at,
                    Event.first_reported_at,
                )
                >= moment
            )
            .where(distance <= max_distance)
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return await self._hydrate_anchors(cast(Sequence[_AnchorRow], rows))

    async def _hydrate_anchors(
        self,
        rows: Sequence[_AnchorRow],
    ) -> list[RelationshipAnchorEvent]:
        if not rows:
            return []
        event_ids = [row.id for row in rows]
        members = await self._membership.current_members(event_ids)
        by_event: dict[uuid.UUID, list[MemberRecord]] = {}
        for member in members:
            by_event.setdefault(member.event_id, []).append(member)

        anchors: list[RelationshipAnchorEvent] = []
        for row in rows:
            event_id = row.id
            raw_embedding = row.embedding
            embedding: tuple[float, ...] | None = (
                tuple(float(v) for v in raw_embedding)
                if raw_embedding is not None
                else None
            )
            raw_lat = row.latitude
            raw_lng = row.longitude
            raw_event_time = row.event_time
            raw_latest = row.latest_published_at
            actors, actor_keys = _extract_actors(getattr(row, "actors", None))
            anchors.append(
                RelationshipAnchorEvent(
                    id=event_id,
                    ai_headline=row.ai_headline,
                    ai_summary=row.ai_summary,
                    category=row.category,
                    country_code=row.country_code,
                    location_name=row.location_name,
                    latitude=float(raw_lat) if raw_lat is not None else None,
                    longitude=float(raw_lng) if raw_lng is not None else None,
                    event_time=(
                        ensure_utc(raw_event_time) if raw_event_time is not None else None
                    ),
                    latest_published_at=(
                        ensure_utc(raw_latest) if raw_latest is not None else None
                    ),
                    first_reported_at=ensure_utc(row.first_reported_at),
                    importance_score=float(row.importance_score),
                    member_hash=row.member_hash,
                    version=int(row.version),
                    embedding=embedding,
                    embedding_model=row.embedding_model,
                    entities=_extract_entities(by_event.get(event_id, ())),
                    actors=actors,
                    actor_keys=actor_keys,
                )
            )
        return anchors

    async def existing_pair_hashes(
        self,
        pair_keys: Sequence[tuple[uuid.UUID, uuid.UUID]],
    ) -> dict[tuple[uuid.UUID, uuid.UUID], str]:
        if not pair_keys:
            return {}
        target_keys = {canonical_pair_key(left, right) for left, right in pair_keys}
        all_ids = sorted({event_id for pair in target_keys for event_id in pair})
        stmt = (
            select(
                EventRelationship.source_event_id,
                EventRelationship.target_event_id,
                EventRelationship.pair_hash,
            )
            .where(EventRelationship.source_event_id.in_(all_ids))
            .where(EventRelationship.target_event_id.in_(all_ids))
        )
        rows = (await self._session.execute(stmt)).all()
        hashes: dict[tuple[uuid.UUID, uuid.UUID], str] = {}
        for source_id, target_id, pair_hash in rows:
            key = canonical_pair_key(source_id, target_id)
            if key in target_keys:
                hashes[key] = pair_hash
        return hashes

    async def upsert_relationship(
        self,
        *,
        source_event_id: uuid.UUID,
        target_event_id: uuid.UUID,
        relationship_type: EventRelationshipType,
        confidence: float,
        rationale: str,
        pair_hash: str,
    ) -> EventRelationship:
        if source_event_id == target_event_id:
            raise ValueError("source_event_id and target_event_id must be distinct.")

        cleaned_rationale = " ".join(rationale.split())[:300]
        clamped_confidence = max(0.0, min(1.0, float(confidence)))

        stmt = select(EventRelationship).where(
            or_(
                and_(
                    EventRelationship.source_event_id == source_event_id,
                    EventRelationship.target_event_id == target_event_id,
                ),
                and_(
                    EventRelationship.source_event_id == target_event_id,
                    EventRelationship.target_event_id == source_event_id,
                ),
            )
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            existing.source_event_id = source_event_id
            existing.target_event_id = target_event_id
            existing.relationship_type = relationship_type
            existing.confidence = clamped_confidence
            existing.rationale = cleaned_rationale
            existing.pair_hash = pair_hash
            existing.updated_at = datetime.now(UTC)
            await self._session.flush()
            return existing

        relationship = EventRelationship(
            source_event_id=source_event_id,
            target_event_id=target_event_id,
            relationship_type=relationship_type,
            confidence=clamped_confidence,
            rationale=cleaned_rationale,
            pair_hash=pair_hash,
        )
        self._session.add(relationship)
        await self._session.flush()
        return relationship

    async def relationships_for_event(
        self,
        event_id: uuid.UUID,
    ) -> list[EventRelationshipView]:
        source_ev = aliased(Event)
        target_ev = aliased(Event)
        stmt = (
            select(
                EventRelationship.id,
                EventRelationship.source_event_id,
                EventRelationship.target_event_id,
                EventRelationship.relationship_type,
                EventRelationship.confidence,
                EventRelationship.rationale,
                source_ev.ai_headline.label("src_headline"),
                source_ev.category.label("src_category"),
                source_ev.category_color.label("src_color"),
                source_ev.location_name.label("src_location"),
                ST_Y(source_ev.location).label("src_lat"),
                ST_X(source_ev.location).label("src_lng"),
                source_ev.importance_score.label("src_score"),
                source_ev.event_time.label("src_time"),
                target_ev.ai_headline.label("tgt_headline"),
                target_ev.category.label("tgt_category"),
                target_ev.category_color.label("tgt_color"),
                target_ev.location_name.label("tgt_location"),
                ST_Y(target_ev.location).label("tgt_lat"),
                ST_X(target_ev.location).label("tgt_lng"),
                target_ev.importance_score.label("tgt_score"),
                target_ev.event_time.label("tgt_time"),
            )
            .join(source_ev, source_ev.id == EventRelationship.source_event_id)
            .join(target_ev, target_ev.id == EventRelationship.target_event_id)
            .where(
                or_(
                    EventRelationship.source_event_id == event_id,
                    EventRelationship.target_event_id == event_id,
                )
            )
            .where(source_ev.merged_into_id.is_(None))
            .where(target_ev.merged_into_id.is_(None))
            .where(source_ev.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
            .where(target_ev.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
            .where(source_ev.selection_tier != SelectionTier.DROP)
            .where(target_ev.selection_tier != SelectionTier.DROP)
            .order_by(EventRelationship.confidence.desc())
        )
        rows = (await self._session.execute(stmt)).all()
        views: list[EventRelationshipView] = []
        for row in rows:
            is_outgoing = row.source_event_id == event_id
            direction: RelationshipDirection = "OUTGOING" if is_outgoing else "INCOMING"
            related_id = row.target_event_id if is_outgoing else row.source_event_id
            related_headline = row.tgt_headline if is_outgoing else row.src_headline
            related_category = row.tgt_category if is_outgoing else row.src_category
            related_color = row.tgt_color if is_outgoing else row.src_color
            related_location = row.tgt_location if is_outgoing else row.src_location
            related_lat = row.tgt_lat if is_outgoing else row.src_lat
            related_lng = row.tgt_lng if is_outgoing else row.src_lng
            related_score = row.tgt_score if is_outgoing else row.src_score
            related_time = row.tgt_time if is_outgoing else row.src_time
            views.append(
                EventRelationshipView(
                    id=row.id,
                    relationship_type=EventRelationshipType(row.relationship_type),
                    direction=direction,
                    confidence=float(row.confidence),
                    rationale=row.rationale,
                    related_event_id=related_id,
                    related_headline=related_headline,
                    related_category=related_category,
                    related_category_color=related_color,
                    related_location_name=related_location,
                    related_latitude=(
                        float(related_lat) if related_lat is not None else None
                    ),
                    related_longitude=(
                        float(related_lng) if related_lng is not None else None
                    ),
                    related_importance_score=float(related_score),
                    related_event_time=(
                        ensure_utc(related_time) if related_time is not None else None
                    ),
                )
            )
        views.sort(
            key=lambda item: (item.confidence, item.related_importance_score),
            reverse=True,
        )
        return views

    async def relationships_for_event_ids(
        self,
        event_ids: Sequence[uuid.UUID],
        *,
        limit: int = 400,
    ) -> list[MapRelationshipView]:
        if not event_ids:
            return []
        source_ev = aliased(Event)
        target_ev = aliased(Event)
        stmt = (
            select(
                EventRelationship.id,
                EventRelationship.source_event_id,
                EventRelationship.target_event_id,
                EventRelationship.relationship_type,
                EventRelationship.confidence,
                EventRelationship.rationale,
                source_ev.ai_headline.label("src_headline"),
                source_ev.category.label("src_category"),
                source_ev.category_color.label("src_color"),
                source_ev.location_name.label("src_location"),
                ST_Y(source_ev.location).label("src_lat"),
                ST_X(source_ev.location).label("src_lng"),
                target_ev.ai_headline.label("tgt_headline"),
                target_ev.category.label("tgt_category"),
                target_ev.category_color.label("tgt_color"),
                target_ev.location_name.label("tgt_location"),
                ST_Y(target_ev.location).label("tgt_lat"),
                ST_X(target_ev.location).label("tgt_lng"),
            )
            .join(source_ev, source_ev.id == EventRelationship.source_event_id)
            .join(target_ev, target_ev.id == EventRelationship.target_event_id)
            .where(
                or_(
                    EventRelationship.source_event_id.in_(event_ids),
                    EventRelationship.target_event_id.in_(event_ids),
                )
            )
            .where(source_ev.merged_into_id.is_(None))
            .where(target_ev.merged_into_id.is_(None))
            .where(source_ev.status == EventStatus.ACTIVE)
            .where(target_ev.status == EventStatus.ACTIVE)
            .where(source_ev.selection_tier != SelectionTier.DROP)
            .where(target_ev.selection_tier != SelectionTier.DROP)
            .where(source_ev.location.is_not(None))
            .where(target_ev.location.is_not(None))
            .order_by(EventRelationship.confidence.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            MapRelationshipView(
                id=row.id,
                source_event_id=row.source_event_id,
                target_event_id=row.target_event_id,
                source_headline=row.src_headline,
                source_category=row.src_category,
                source_category_color=row.src_color,
                source_location_name=row.src_location,
                source_latitude=float(row.src_lat),
                source_longitude=float(row.src_lng),
                target_headline=row.tgt_headline,
                target_category=row.tgt_category,
                target_category_color=row.tgt_color,
                target_location_name=row.tgt_location,
                target_latitude=float(row.tgt_lat),
                target_longitude=float(row.tgt_lng),
                relationship_type=EventRelationshipType(row.relationship_type),
                confidence=float(row.confidence),
                rationale=row.rationale,
            )
            for row in rows
            if row.src_lat is not None
            and row.src_lng is not None
            and row.tgt_lat is not None
            and row.tgt_lng is not None
        ]

    async def counts_for_events(
        self,
        event_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, int]:
        if not event_ids:
            return {}
        target_ids = set(event_ids)
        source_ev = aliased(Event)
        target_ev = aliased(Event)
        stmt = (
            select(
                EventRelationship.source_event_id,
                EventRelationship.target_event_id,
            )
            .join(source_ev, source_ev.id == EventRelationship.source_event_id)
            .join(target_ev, target_ev.id == EventRelationship.target_event_id)
            .where(
                or_(
                    EventRelationship.source_event_id.in_(event_ids),
                    EventRelationship.target_event_id.in_(event_ids),
                )
            )
            .where(source_ev.merged_into_id.is_(None))
            .where(target_ev.merged_into_id.is_(None))
            .where(source_ev.status == EventStatus.ACTIVE)
            .where(target_ev.status == EventStatus.ACTIVE)
            .where(source_ev.selection_tier != SelectionTier.DROP)
            .where(target_ev.selection_tier != SelectionTier.DROP)
        )
        counts: dict[uuid.UUID, int] = {event_id: 0 for event_id in target_ids}
        for source_id, target_id in (await self._session.execute(stmt)).all():
            if source_id in counts:
                counts[source_id] += 1
            if target_id in counts:
                counts[target_id] += 1
        return counts
