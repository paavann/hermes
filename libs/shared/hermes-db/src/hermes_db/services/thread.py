from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import (
    EventStatus,
    ImpactLevel,
    ThreadKind,
    ThreadStatus,
    VerificationStatus,
)
from hermes_db.models.event import Event
from hermes_db.models.thread import Thread
from hermes_db.services.event_membership import EventMembershipService, MemberRecord
from hermes_db.utils.datetime import ensure_utc


THREAD_DORMANT_DAYS = 7
THREAD_ENDED_DAYS = 30
THREAD_IMPORTANCE_HALF_LIFE_HOURS = 168.0


def normalize_name(value: str) -> str:
    return " ".join(value.split()).casefold()[:255]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for left_value, right_value in zip(left, right, strict=True):
        dot += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / math.sqrt(left_norm * right_norm)


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


@dataclass(frozen=True, slots=True)
class ThreadEventSnapshot:
    id: uuid.UUID
    ai_headline: str
    ai_summary: str | None
    category: str
    event_time: datetime | None
    latest_published_at: datetime | None
    first_reported_at: datetime
    importance_score: float
    latitude: float | None
    longitude: float | None
    embedding: tuple[float, ...] | None
    embedding_model: str | None
    facts: tuple[str, ...]
    entities: frozenset[str]
    locations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ThreadCandidate:
    id: uuid.UUID
    name: str
    description: str | None
    kind: ThreadKind
    status: ThreadStatus
    last_event_at: datetime | None
    importance: float
    event_count: int
    embedding: tuple[float, ...] | None
    embedding_model: str | None
    entities: frozenset[str]


@dataclass(frozen=True, slots=True)
class ThreadMatch:
    candidate: ThreadCandidate
    score: float
    embedding_similarity: float
    entity_similarity: float


@dataclass(frozen=True, slots=True)
class ThreadEventView:
    id: uuid.UUID
    ai_headline: str
    ai_summary: str | None
    category: str
    category_color: str
    impact_level: ImpactLevel
    importance_score: float
    verification_status: VerificationStatus
    location_name: str | None
    latitude: float | None
    longitude: float | None
    first_reported_at: datetime
    last_updated_at: datetime


class ThreadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._membership = EventMembershipService(session)

    async def create_thread(
        self,
        name: str,
        *,
        kind: ThreadKind = ThreadKind.DEVELOPING,
        description: str | None = None,
        entities: list[dict[str, object]] | None = None,
        keywords: list[str] | None = None,
        started_at: datetime | None = None,
        embedding: Sequence[float] | None = None,
        embedding_model: str | None = None,
        last_event_at: datetime | None = None,
    ) -> Thread:
        thread = Thread(
            name=name[:255],
            name_norm=normalize_name(name),
            kind=kind,
            description=description,
            entities=entities or [],
            keywords=keywords or [],
            started_at=ensure_utc(started_at) if started_at is not None else None,
            last_event_at=(
                ensure_utc(last_event_at) if last_event_at is not None else None
            ),
            embedding=list(embedding) if embedding is not None else None,
            embedding_model=embedding_model,
            event_count=0,
        )
        self._session.add(thread)
        await self._session.flush()
        return thread

    async def get_thread(self, thread_id: uuid.UUID) -> Thread | None:
        return await self._session.get(Thread, thread_id)

    async def thread_events(
        self,
        thread_id: uuid.UUID,
    ) -> list[ThreadEventView]:
        stmt = (
            select(
                Event.id,
                Event.ai_headline,
                Event.ai_summary,
                Event.category,
                Event.category_color,
                Event.impact_level,
                Event.importance_score,
                Event.verification_status,
                Event.location_name,
                ST_Y(Event.location).label("latitude"),
                ST_X(Event.location).label("longitude"),
                Event.first_reported_at,
                Event.last_updated_at,
            )
            .where(Event.thread_id == thread_id)
            .where(Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
            .where(Event.merged_into_id.is_(None))
            .order_by(Event.first_reported_at)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            ThreadEventView(
                id=row.id,
                ai_headline=row.ai_headline,
                ai_summary=row.ai_summary,
                category=row.category,
                category_color=row.category_color,
                impact_level=row.impact_level,
                importance_score=row.importance_score,
                verification_status=row.verification_status,
                location_name=row.location_name,
                latitude=float(row.latitude) if row.latitude is not None else None,
                longitude=float(row.longitude) if row.longitude is not None else None,
                first_reported_at=ensure_utc(row.first_reported_at),
                last_updated_at=ensure_utc(row.last_updated_at),
            )
            for row in rows
        ]

    async def list_threads(
        self,
        *,
        statuses: Sequence[ThreadStatus] = (
            ThreadStatus.ACTIVE,
            ThreadStatus.DORMANT,
        ),
        limit: int = 100,
    ) -> list[Thread]:
        stmt = (
            select(Thread)
            .where(Thread.status.in_(list(statuses)))
            .order_by(Thread.importance.desc(), Thread.last_event_at.desc().nullslast())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def assign_event(
        self,
        event_id: uuid.UUID,
        thread_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> bool:
        moment = now or datetime.now(UTC)
        result = await self._session.execute(
            update(Event)
            .where(Event.id == event_id)
            .values(thread_id=thread_id, last_updated_at=moment)
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(
            update(Thread)
            .where(Thread.id == thread_id)
            .values(
                status=ThreadStatus.ACTIVE,
                last_event_at=moment,
                ended_at=None,
            )
            .execution_options(synchronize_session=False)
        )
        await self.recompute(thread_id, now=moment)
        return isinstance(result, CursorResult) and bool(result.rowcount)

    async def recompute(
        self,
        thread_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> Thread | None:
        moment = now or datetime.now(UTC)
        thread = await self._session.get(Thread, thread_id)
        if thread is None:
            return None

        stmt = (
            select(
                Event.id,
                Event.importance_score,
                Event.event_time,
                Event.latest_published_at,
                Event.first_reported_at,
                Event.embedding,
            )
            .where(Event.thread_id == thread_id)
            .where(Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
            .where(Event.merged_into_id.is_(None))
        )
        rows = (await self._session.execute(stmt)).all()
        event_ids = [row.id for row in rows]
        members = await self._membership.current_members(event_ids)

        timestamps = [
            ensure_utc(row.latest_published_at)
            if row.latest_published_at is not None
            else (
                ensure_utc(row.event_time)
                if row.event_time is not None
                else ensure_utc(row.first_reported_at)
            )
            for row in rows
        ]
        last_event_at = max(timestamps) if timestamps else None
        age_hours = (
            max(0.0, (ensure_utc(moment) - last_event_at).total_seconds() / 3600.0)
            if last_event_at is not None
            else 0.0
        )
        max_importance = max((row.importance_score for row in rows), default=0.0)
        importance = max_importance * math.exp(
            -age_hours / THREAD_IMPORTANCE_HALF_LIFE_HOURS
        )

        embeddings = [row.embedding for row in rows if row.embedding is not None]
        centroid: tuple[float, ...] | None = None
        if embeddings:
            width = len(embeddings[0])
            centroid = tuple(
                sum(float(vector[index]) for vector in embeddings) / len(embeddings)
                for index in range(width)
            )

        entity_map: dict[str, str] = {}
        keyword_counts: dict[str, int] = {}
        for member in members:
            for entity in member.entities:
                name = entity.get("name")
                kind = entity.get("kind")
                if isinstance(name, str) and name.strip():
                    entity_map.setdefault(
                        name.strip(),
                        kind if isinstance(kind, str) else "OTHER",
                    )
            if member.fact:
                for token in member.fact.casefold().split():
                    cleaned = token.strip(".,;:!?()[]\"'")
                    if len(cleaned) >= 5:
                        keyword_counts[cleaned] = keyword_counts.get(cleaned, 0) + 1
        top_entities = sorted(entity_map.items())[:12]
        keywords = [
            token
            for token, _count in sorted(
                keyword_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:10]
        ]

        thread.event_count = len(rows)
        thread.last_event_at = last_event_at
        thread.importance = round(importance, 2)
        thread.embedding = list(centroid) if centroid is not None else None
        thread.entities = [{"name": name, "kind": kind} for name, kind in top_entities]
        thread.keywords = keywords
        thread.name_norm = normalize_name(thread.name)
        return thread

    async def unthreaded_events(
        self,
        *,
        limit: int = 200,
    ) -> list[ThreadEventSnapshot]:
        stmt = (
            select(
                Event.id,
                Event.ai_headline,
                Event.ai_summary,
                Event.category,
                Event.event_time,
                Event.latest_published_at,
                Event.first_reported_at,
                Event.importance_score,
                ST_Y(Event.location).label("latitude"),
                ST_X(Event.location).label("longitude"),
                Event.embedding,
                Event.embedding_model,
            )
            .where(Event.status == EventStatus.ACTIVE)
            .where(Event.merged_into_id.is_(None))
            .where(Event.thread_id.is_(None))
            .order_by(Event.importance_score.desc(), Event.first_reported_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        members = await self._membership.current_members([row.id for row in rows])
        by_event: dict[uuid.UUID, list[MemberRecord]] = {}
        for member in members:
            by_event.setdefault(member.event_id, []).append(member)

        snapshots: list[ThreadEventSnapshot] = []
        for row in rows:
            event_members = by_event.get(row.id, [])
            facts = tuple(member.fact for member in event_members if member.fact)
            entities = frozenset(
                name.strip().casefold()
                for member in event_members
                for entity in member.entities
                if isinstance((name := entity.get("name")), str) and name.strip()
            )
            locations = tuple(
                name
                for member in event_members
                for location in member.locations
                if isinstance((name := location.get("name")), str) and name.strip()
            )
            embedding: tuple[float, ...] | None = None
            if row.embedding is not None:
                embedding = tuple(float(value) for value in row.embedding)
            snapshots.append(
                ThreadEventSnapshot(
                    id=row.id,
                    ai_headline=row.ai_headline,
                    ai_summary=row.ai_summary,
                    category=row.category,
                    event_time=ensure_utc(row.event_time)
                    if row.event_time is not None
                    else None,
                    latest_published_at=ensure_utc(row.latest_published_at)
                    if row.latest_published_at is not None
                    else None,
                    first_reported_at=ensure_utc(row.first_reported_at),
                    importance_score=row.importance_score,
                    latitude=float(row.latitude) if row.latitude is not None else None,
                    longitude=float(row.longitude)
                    if row.longitude is not None
                    else None,
                    embedding=embedding,
                    embedding_model=row.embedding_model,
                    facts=facts,
                    entities=entities,
                    locations=locations,
                )
            )
        return snapshots

    async def candidates(
        self,
        event: ThreadEventSnapshot,
        *,
        limit: int = 40,
    ) -> list[ThreadCandidate]:
        stmt = (
            select(
                Thread.id,
                Thread.name,
                Thread.description,
                Thread.kind,
                Thread.status,
                Thread.last_event_at,
                Thread.importance,
                Thread.event_count,
                Thread.embedding,
                Thread.embedding_model,
                Thread.entities,
            )
            .where(Thread.status.in_([ThreadStatus.ACTIVE, ThreadStatus.DORMANT]))
            .order_by(Thread.last_event_at.desc().nullslast())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        candidates: list[ThreadCandidate] = []
        for row in rows:
            embedding: tuple[float, ...] | None = None
            if row.embedding is not None:
                embedding = tuple(float(value) for value in row.embedding)
            entities = frozenset(
                name.strip().casefold()
                for entity in (row.entities or [])
                if isinstance((name := entity.get("name")), str) and name.strip()
            )
            candidates.append(
                ThreadCandidate(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    kind=row.kind,
                    status=row.status,
                    last_event_at=ensure_utc(row.last_event_at)
                    if row.last_event_at is not None
                    else None,
                    importance=row.importance,
                    event_count=row.event_count,
                    embedding=embedding,
                    embedding_model=row.embedding_model,
                    entities=entities,
                )
            )
        return candidates

    async def ranked_candidates(
        self,
        event: ThreadEventSnapshot,
        *,
        limit: int = 40,
    ) -> list[ThreadMatch]:
        """Rank candidate threads by embedding cosine and entity overlap.

        The SQL prefilter keeps the pool bounded; the final score is computed
        in Python so entity blocking does not require a JSONB index.
        """
        candidates = await self.candidates(event, limit=limit)
        event_entities = event.entities
        matches: list[ThreadMatch] = []
        for candidate in candidates:
            embedding_similarity = 0.0
            if (
                event.embedding is not None
                and candidate.embedding is not None
                and event.embedding_model == candidate.embedding_model
                and len(event.embedding) == len(candidate.embedding)
            ):
                embedding_similarity = max(
                    0.0,
                    _cosine(event.embedding, candidate.embedding),
                )
            entity_similarity = _jaccard(event_entities, candidate.entities)
            score = 0.70 * embedding_similarity + 0.30 * entity_similarity
            matches.append(
                ThreadMatch(
                    candidate=candidate,
                    score=round(score, 4),
                    embedding_similarity=round(embedding_similarity, 4),
                    entity_similarity=round(entity_similarity, 4),
                )
            )
        matches.sort(key=lambda match: match.score, reverse=True)
        return matches

    async def run_lifecycle(
        self,
        *,
        now: datetime | None = None,
        dormant_days: int = THREAD_DORMANT_DAYS,
        ended_days: int = THREAD_ENDED_DAYS,
    ) -> dict[str, int]:
        moment = now or datetime.now(UTC)
        dormant_cutoff = moment - timedelta(days=dormant_days)
        ended_cutoff = moment - timedelta(days=ended_days)

        dormant = await self._session.execute(
            update(Thread)
            .where(Thread.status == ThreadStatus.ACTIVE)
            .where(Thread.last_event_at.is_not(None))
            .where(Thread.last_event_at < dormant_cutoff)
            .values(status=ThreadStatus.DORMANT)
            .execution_options(synchronize_session=False)
        )
        ended = await self._session.execute(
            update(Thread)
            .where(Thread.status == ThreadStatus.DORMANT)
            .where(Thread.last_event_at.is_not(None))
            .where(Thread.last_event_at < ended_cutoff)
            .values(
                status=ThreadStatus.ENDED,
                ended_at=moment,
            )
            .execution_options(synchronize_session=False)
        )
        return {
            "dormant": int(dormant.rowcount or 0)
            if isinstance(dormant, CursorResult)
            else 0,
            "ended": int(ended.rowcount or 0)
            if isinstance(ended, CursorResult)
            else 0,
        }

    async def count(self, status: ThreadStatus | None = None) -> int:
        stmt = select(func.count()).select_from(Thread)
        if status is not None:
            stmt = stmt.where(Thread.status == status)
        return int(await self._session.scalar(stmt) or 0)
