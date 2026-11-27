from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import (
    ArticleCertainty,
    ArticleType,
    AssignmentMethod,
    CredibilityTier,
    EventStatus,
    VerificationStatus,
)
from hermes_db.models.article import Article
from hermes_db.models.article_family import ArticleFamily
from hermes_db.models.article_label import ArticleLabel
from hermes_db.models.event import Event
from hermes_db.models.event_member import EventMember
from hermes_db.models.source import Source
from hermes_db.services.verification import (
    MemberEvidence,
    VerificationResult,
    compute_verification,
)
from hermes_db.utils.datetime import ensure_utc


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MemberRecord:
    """One current member with the fields aggregation and scoring need."""

    event_id: uuid.UUID
    article_id: uuid.UUID
    family_id: uuid.UUID | None
    source_id: uuid.UUID | None
    source_name: str | None
    source_origin_group: str | None
    source_slug: str | None
    source_credibility: CredibilityTier | None
    published_at: datetime | None
    embedding: tuple[float, ...] | None
    embedding_model: str | None
    input_quality: float | None
    article_type: ArticleType | None
    fact: str | None
    certainty: ArticleCertainty | None
    consequence: int | None
    specificity: int | None
    scale_facts: tuple[tuple[str, object], ...]
    entities: tuple[dict[str, object], ...]
    locations: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class EventAggregate:
    article_count: int
    source_count: int
    family_count: int
    independent_origin_count: int
    verification_status: VerificationStatus
    latest_published_at: datetime | None
    first_published_at: datetime | None
    centroid: tuple[float, ...] | None
    embedding_model: str | None


def _latest_label_subquery():
    rank = (
        func.row_number()
        .over(
            partition_by=ArticleLabel.article_id,
            order_by=(ArticleLabel.labeled_at.desc(), ArticleLabel.id),
        )
        .label("rank")
    )
    return (
        select(
            ArticleLabel.article_id.label("article_id"),
            ArticleLabel.fact.label("fact"),
            ArticleLabel.certainty.label("certainty"),
            ArticleLabel.consequence.label("consequence"),
            ArticleLabel.specificity.label("specificity"),
            ArticleLabel.article_type.label("article_type"),
            ArticleLabel.scale_facts.label("scale_facts"),
            ArticleLabel.entities.label("entities"),
            ArticleLabel.locations.label("locations"),
            rank,
        )
        .subquery("ranked_labels")
    )


class EventMembershipService:
    """Owns current membership, history, and event aggregate fields.

    Every method leaves the transaction boundary to the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def current_members(
        self,
        event_ids: Sequence[uuid.UUID],
    ) -> list[MemberRecord]:
        if not event_ids:
            return []
        labels = _latest_label_subquery()
        stmt = (
            select(
                EventMember.event_id,
                Article.id,
                Article.family_id,
                Article.source_id,
                Source.name,
                Source.origin_group,
                Source.slug,
                Source.credibility,
                Article.published_at,
                Article.embedding,
                Article.embedding_model,
                Article.input_quality,
                labels.c.fact,
                labels.c.certainty,
                labels.c.consequence,
                labels.c.specificity,
                labels.c.article_type,
                labels.c.scale_facts,
                labels.c.entities,
                labels.c.locations,
            )
            .join(Article, Article.id == EventMember.article_id)
            .join(Source, Source.id == Article.source_id, isouter=True)
            .join(labels, labels.c.article_id == Article.id, isouter=True)
            .where(EventMember.event_id.in_(event_ids))
            .where(EventMember.is_current.is_(True))
            .where((labels.c.rank.is_(None)) | (labels.c.rank == 1))
            .order_by(EventMember.event_id, Article.published_at.nullslast(), Article.id)
        )
        rows = (await self._session.execute(stmt)).all()
        records: list[MemberRecord] = []
        for row in rows:
            embedding: tuple[float, ...] | None = None
            if row.embedding is not None:
                embedding = tuple(float(value) for value in row.embedding)
            records.append(
                MemberRecord(
                    event_id=row.event_id,
                    article_id=row.id,
                    family_id=row.family_id,
                    source_id=row.source_id,
                    source_name=row.name,
                    source_origin_group=row.origin_group,
                    source_slug=row.slug,
                    source_credibility=(
                        CredibilityTier(row.credibility)
                        if row.credibility is not None
                        else None
                    ),
                    published_at=ensure_utc(row.published_at)
                    if row.published_at is not None
                    else None,
                    embedding=embedding,
                    embedding_model=row.embedding_model,
                    input_quality=row.input_quality,
                    article_type=(
                        ArticleType(row.article_type)
                        if row.article_type is not None
                        else None
                    ),
                    fact=row.fact,
                    certainty=row.certainty,
                    consequence=row.consequence,
                    specificity=row.specificity,
                    scale_facts=tuple((row.scale_facts or {}).items()),
                    entities=tuple(row.entities or ()),
                    locations=tuple(row.locations or ()),
                )
            )
        return records

    async def family_origin_groups(
        self,
        family_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, str]:
        if not family_ids:
            return {}
        stmt = select(ArticleFamily.id, ArticleFamily.primary_origin_group).where(
            ArticleFamily.id.in_(family_ids)
        )
        rows = (await self._session.execute(stmt)).all()
        return {row.id: row.primary_origin_group for row in rows}

    async def add_member(
        self,
        *,
        event_id: uuid.UUID,
        article_id: uuid.UUID,
        method: AssignmentMethod,
        confidence: float | None,
        score_breakdown: dict[str, object],
        assigned_at: datetime | None = None,
    ) -> EventMember:
        now = assigned_at or datetime.now(UTC)
        member = EventMember(
            event_id=event_id,
            article_id=article_id,
            assigned_at=now,
            method=method,
            confidence=confidence,
            score_breakdown=score_breakdown,
            is_current=True,
        )
        self._session.add(member)
        await self._session.execute(
            update(Article)
            .where(Article.id == article_id)
            .values(
                event_id=event_id,
                assigned_at=now,
                assignment_method=method,
                assignment_confidence=confidence,
            )
            .execution_options(synchronize_session=False)
        )
        return member

    async def remove_members(
        self,
        event_id: uuid.UUID,
        article_ids: Sequence[uuid.UUID],
        *,
        removed_at: datetime | None = None,
    ) -> int:
        if not article_ids:
            return 0
        now = removed_at or datetime.now(UTC)
        stmt = (
            update(EventMember)
            .where(EventMember.event_id == event_id)
            .where(EventMember.article_id.in_(article_ids))
            .where(EventMember.is_current.is_(True))
            .values(is_current=False, removed_at=now)
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return int(result.rowcount or 0)
        return 0

    async def recompute(self, event_id: uuid.UUID) -> EventAggregate:
        """Recompute counts, verification, timestamps, and centroid."""
        members = await self.current_members([event_id])
        family_ids = [m.family_id for m in members if m.family_id is not None]
        family_origins = await self.family_origin_groups(family_ids)

        evidence = [
            MemberEvidence(
                article_id=member.article_id,
                family_id=member.family_id,
                family_origin_group=(
                    family_origins.get(member.family_id)
                    if member.family_id is not None
                    else None
                ),
                source_id=member.source_id,
                source_origin_group=member.source_origin_group,
                source_slug=member.source_slug,
                certainty=member.certainty,
            )
            for member in members
        ]
        verification: VerificationResult = compute_verification(evidence)

        embeddings = [m.embedding for m in members if m.embedding is not None]
        centroid: tuple[float, ...] | None = None
        if embeddings:
            count = len(embeddings)
            width = len(embeddings[0])
            centroid = tuple(
                sum(vector[index] for vector in embeddings) / count
                for index in range(width)
            )
        embedding_model = next(
            (m.embedding_model for m in members if m.embedding_model is not None),
            None,
        )
        published = [m.published_at for m in members if m.published_at is not None]
        latest = max(published) if published else None
        earliest = min(published) if published else None

        await self._session.execute(
            update(Event)
            .where(Event.id == event_id)
            .values(
                article_count=len(members),
                source_count=verification.source_count,
                family_count=verification.family_count,
                independent_origin_count=verification.independent_origin_count,
                verification_status=verification.status,
                latest_published_at=latest,
                last_member_added_at=datetime.now(UTC),
                embedding=list(centroid) if centroid is not None else None,
                embedding_model=embedding_model,
            )
            .execution_options(synchronize_session=False)
        )
        return EventAggregate(
            article_count=len(members),
            source_count=verification.source_count,
            family_count=verification.family_count,
            independent_origin_count=verification.independent_origin_count,
            verification_status=verification.status,
            latest_published_at=latest,
            first_published_at=earliest,
            centroid=centroid,
            embedding_model=embedding_model,
        )

    async def reactivate(self, event_id: uuid.UUID) -> bool:
        stmt = (
            update(Event)
            .where(Event.id == event_id)
            .where(Event.status == EventStatus.STALE)
            .values(status=EventStatus.ACTIVE)
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        return bool(isinstance(result, CursorResult) and result.rowcount)
