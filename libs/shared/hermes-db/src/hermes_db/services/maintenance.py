from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import EventStatus, IngestStatus
from hermes_db.models.article import Article
from hermes_db.models.article_label import ArticleLabel
from hermes_db.models.cluster_decision import ClusterDecision
from hermes_db.models.event import Event
from hermes_db.models.event_member import EventMember
from hermes_db.services.event_lifecycle import EventLifecycleService
from hermes_db.services.event_membership import EventMembershipService


@dataclass(frozen=True, slots=True)
class ConsistencyReport:
    count_drift: int
    events_without_members: int
    missing_embeddings: int
    failed_claims: int
    orphan_labels: int


@dataclass(frozen=True, slots=True)
class RetentionResult:
    cluster_decisions: int
    removed_members: int
    archived_embeddings: int


class MaintenanceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._membership = EventMembershipService(session)

    async def reconcile_counts(
        self,
        *,
        after_id: uuid.UUID | None = None,
        limit: int = 1000,
    ) -> list[uuid.UUID]:
        stmt = (
            select(Event.id)
            .where(Event.merged_into_id.is_(None))
            .order_by(Event.id)
            .limit(limit)
        )
        if after_id is not None:
            stmt = stmt.where(Event.id > after_id)
        event_ids = list((await self._session.execute(stmt)).scalars().all())
        for event_id in event_ids:
            await self._membership.recompute(event_id)
        return event_ids

    async def consistency_report(self) -> ConsistencyReport:
        actual = (
            select(
                EventMember.event_id.label("event_id"),
                func.count().label("member_count"),
            )
            .where(EventMember.is_current.is_(True))
            .group_by(EventMember.event_id)
            .subquery("actual_members")
        )
        drift_sq = (
            select(func.count())
            .select_from(Event)
            .outerjoin(actual, actual.c.event_id == Event.id)
            .where(Event.merged_into_id.is_(None))
            .where(Event.article_count != func.coalesce(actual.c.member_count, 0))
            .scalar_subquery()
        )
        without_members_sq = (
            select(func.count())
            .select_from(Event)
            .outerjoin(actual, actual.c.event_id == Event.id)
            .where(Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
            .where(func.coalesce(actual.c.member_count, 0) == 0)
            .scalar_subquery()
        )
        missing_embeddings_sq = (
            select(func.count())
            .select_from(Article)
            .where(Article.ingest_status == IngestStatus.LABELED)
            .where(Article.embedding.is_(None))
            .scalar_subquery()
        )
        failed_claims_sq = (
            select(func.count())
            .select_from(Article)
            .where(Article.ingest_status == IngestStatus.FAILED)
            .scalar_subquery()
        )
        orphan_labels_sq = (
            select(func.count())
            .select_from(ArticleLabel)
            .outerjoin(Article, Article.id == ArticleLabel.article_id)
            .where(Article.id.is_(None))
            .scalar_subquery()
        )
        row = (
            await self._session.execute(
                select(
                    drift_sq.label("drift"),
                    without_members_sq.label("without_members"),
                    missing_embeddings_sq.label("missing_embeddings"),
                    failed_claims_sq.label("failed_claims"),
                    orphan_labels_sq.label("orphan_labels"),
                )
            )
        ).one()
        return ConsistencyReport(
            count_drift=int(row.drift or 0),
            events_without_members=int(row.without_members or 0),
            missing_embeddings=int(row.missing_embeddings or 0),
            failed_claims=int(row.failed_claims or 0),
            orphan_labels=int(row.orphan_labels or 0),
        )

    async def apply_retention(
        self,
        *,
        now: datetime | None = None,
    ) -> RetentionResult:
        moment = now or datetime.now(UTC)
        decisions = await self._session.execute(
            delete(ClusterDecision).where(
                ClusterDecision.created_at < moment - timedelta(days=90)
            )
        )
        members = await self._session.execute(
            delete(EventMember)
            .where(EventMember.is_current.is_(False))
            .where(EventMember.removed_at.is_not(None))
            .where(EventMember.removed_at < moment - timedelta(days=180))
        )
        embeddings = await EventLifecycleService(
            self._session
        ).purge_archived_embeddings(now=moment, after_days=30)
        return RetentionResult(
            cluster_decisions=_rowcount(decisions),
            removed_members=_rowcount(members),
            archived_embeddings=embeddings,
        )

    async def requeue_articles(self, *, since: datetime) -> int:
        result = await self._session.execute(
            update(Article)
            .where(Article.ingest_status.in_([IngestStatus.FAILED, IngestStatus.REJECTED]))
            .where(Article.published_at.is_not(None))
            .where(Article.published_at >= since)
            .values(
                ingest_status=IngestStatus.NEW,
                claimed_at=None,
                claimed_by=None,
                last_error=None,
                attempt_count=0,
                reject_stage=None,
                reject_reason=None,
                rejected_at=None,
            )
            .execution_options(synchronize_session=False)
        )
        return _rowcount(result)


def _rowcount(result: object) -> int:
    if isinstance(result, CursorResult):
        return int(result.rowcount or 0)
    return 0
