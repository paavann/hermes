from __future__ import annotations
import uuid
from collections.abc import Sequence
from datetime import datetime
from hermes_db.enums import IngestStatus
from hermes_db.models.article import Article
from sqlalchemy import func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Update


class ArticleQueue:
    """Claim-based work queue over the article ingest status column.
    Every method runs inside the caller's transaction. The stage decides when
    to commit so a crash before commit leaves work claimable by the next run.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def claim_statement(
        *,
        status: IngestStatus,
        limit: int,
        worker_id: str,
        max_attempts: int,
    ) -> Update:
        if limit <= 0:
            raise ValueError("claim limit must be positive.")
        candidates = (
            select(Article.id)
            .where(Article.ingest_status == status)
            .where(Article.attempt_count < max_attempts)
            .order_by(
                Article.published_at.asc().nulls_last(), Article.ingested_at.asc()
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        return (
            update(Article)
            .where(Article.id.in_(candidates))
            .values(
                ingest_status=IngestStatus.ANALYZING,
                claimed_at=func.now(),
                claimed_by=worker_id,
                attempt_count=Article.attempt_count + 1,
                last_error=None,
            )
            .returning(Article)
            .execution_options(synchronize_session=False)
        )

    async def claim(
        self,
        *,
        status: IngestStatus,
        limit: int,
        worker_id: str,
        max_attempts: int,
    ) -> list[Article]:
        stmt = self.claim_statement(
            status=status,
            limit=limit,
            worker_id=worker_id,
            max_attempts=max_attempts,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark(
        self,
        article_ids: Sequence[uuid.UUID],
        status: IngestStatus,
        *,
        error: str | None = None,
    ) -> int:
        ids = list(article_ids)
        if not ids:
            return 0
        stmt = (
            update(Article)
            .where(Article.id.in_(ids))
            .values(
                ingest_status=status,
                claimed_at=None,
                claimed_by=None,
                last_error=error,
            )
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0

    async def fail(
        self,
        article: Article,
        error: str,
        *,
        max_attempts: int,
    ) -> IngestStatus:
        return await self.fail_id(
            article_id=article.id,
            attempt_count=article.attempt_count,
            error=error,
            max_attempts=max_attempts,
        )

    async def fail_id(
        self,
        *,
        article_id: uuid.UUID,
        attempt_count: int,
        error: str,
        max_attempts: int,
    ) -> IngestStatus:
        status = (
            IngestStatus.NEW if attempt_count < max_attempts else IngestStatus.FAILED
        )
        await self.mark([article_id], status, error=error)
        return status

    async def release(self, article_ids: Sequence[uuid.UUID]) -> int:
        """Return claimed articles to NEW without consuming an attempt."""
        ids = list(article_ids)
        if not ids:
            return 0
        stmt = (
            update(Article)
            .where(Article.id.in_(ids))
            .where(Article.ingest_status == IngestStatus.ANALYZING)
            .values(
                ingest_status=IngestStatus.NEW,
                claimed_at=None,
                claimed_by=None,
                last_error=None,
                attempt_count=func.greatest(Article.attempt_count - 1, 0),
            )
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0

    async def requeue_stale(
        self,
        *,
        older_than: datetime,
        limit: int,
        max_attempts: int,
    ) -> tuple[int, int]:
        """Return stale claims to the queue, failing exhausted articles."""
        stmt = (
            select(Article.id, Article.attempt_count)
            .where(Article.ingest_status == IngestStatus.ANALYZING)
            .where(
                or_(
                    Article.claimed_at.is_(None),
                    Article.claimed_at < older_than,
                )
            )
            .order_by(Article.claimed_at.asc().nulls_first())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = (await self._session.execute(stmt)).all()
        requeue_ids = [row.id for row in rows if row.attempt_count < max_attempts]
        failed_ids = [row.id for row in rows if row.attempt_count >= max_attempts]
        if requeue_ids:
            await self.mark(
                requeue_ids,
                IngestStatus.NEW,
                error="stale claim requeued.",
            )
        if failed_ids:
            await self.mark(
                failed_ids,
                IngestStatus.FAILED,
                error="stale claim exhausted retries.",
            )
        return len(requeue_ids), len(failed_ids)

    async def status_counts(self) -> dict[IngestStatus, int]:
        stmt = select(Article.ingest_status, func.count(Article.id)).group_by(
            Article.ingest_status
        )
        rows = (await self._session.execute(stmt)).all()
        return {IngestStatus(status): count for status, count in rows}

    async def count_stale(self, *, older_than: datetime) -> int:
        stmt = (
            select(func.count(Article.id))
            .where(Article.ingest_status == IngestStatus.ANALYZING)
            .where(
                or_(
                    Article.claimed_at.is_(None),
                    Article.claimed_at < older_than,
                )
            )
        )
        count = await self._session.scalar(stmt)
        return int(count or 0)
