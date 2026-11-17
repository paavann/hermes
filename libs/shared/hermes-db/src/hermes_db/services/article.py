import logging
import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import IngestStatus
from hermes_db.models.article import Article
from hermes_db.utils.datetime import ensure_utc


logger = logging.getLogger(__name__)


class ArticleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def article_url_exists(self, url: str) -> bool:
        stmt = select(Article.id).where(Article.url == url).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_article(
        self,
        *,
        title: str,
        url: str,
        event_id: uuid.UUID | None = None,
        source_id: uuid.UUID | None = None,
        published_at: datetime | None = None,
        canonical_url: str | None = None,
        thumbnail_url: str | None = None,
        feed_summary: str | None = None,
        feed_content: str | None = None,
        content_hash: str | None = None,
        title_simhash: str | None = None,
        language: str | None = None,
        ingest_status: IngestStatus = IngestStatus.NEW,
    ) -> Article | None:
        stmt = (
            pg_insert(Article)
            .values(
                event_id=event_id,
                source_id=source_id,
                title=title,
                url=url,
                published_at=(
                    ensure_utc(published_at) if published_at is not None else None
                ),
                canonical_url=canonical_url,
                thumbnail_url=thumbnail_url,
                feed_summary=feed_summary,
                feed_content=feed_content,
                content_hash=content_hash,
                title_simhash=title_simhash,
                language=language,
                ingest_status=ingest_status,
            )
            .on_conflict_do_nothing(index_elements=["url"])
            .returning(Article)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_url(self, url: str) -> Article | None:
        stmt = select(Article).where(Article.url == url).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_content_hash(self, content_hash: str) -> Article | None:
        stmt = select(Article).where(Article.content_hash == content_hash).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_ingest_status(
        self,
        article_ids: Sequence[uuid.UUID],
        status: IngestStatus,
    ) -> int:
        if not article_ids:
            return 0
        stmt = (
            update(Article)
            .where(Article.id.in_(article_ids))
            .values(ingest_status=status)
        )
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0

    async def assign_event(
        self,
        article_ids: Sequence[uuid.UUID],
        event_id: uuid.UUID,
    ) -> int:
        if not article_ids:
            return 0
        stmt = (
            update(Article).where(Article.id.in_(article_ids)).values(event_id=event_id)
        )
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0

    async def clear_event_members(self, event_id: uuid.UUID) -> int:
        stmt = update(Article).where(Article.event_id == event_id).values(event_id=None)
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0

    async def list_event_articles(self, event_id: uuid.UUID) -> list[Article]:
        stmt = (
            select(Article)
            .where(Article.event_id == event_id)
            .order_by(Article.published_at.asc().nulls_last(), Article.id.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_ingest_status(
        self,
        status: IngestStatus,
        *,
        limit: int = 100,
    ) -> list[Article]:
        stmt = (
            select(Article)
            .where(Article.ingest_status == status)
            .order_by(Article.ingested_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
