import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.models.article import Article


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
        event_id: uuid.UUID,
        source_id: uuid.UUID,
        title: str,
        url: str,
        published_at: datetime | None = None,
    ) -> Article | None:
        stmt = (
            pg_insert(Article)
            .values(
                event_id=event_id,
                source_id=source_id,
                title=title,
                url=url,
                published_at=published_at,
            )
            .on_conflict_do_nothing(index_elements=["url"])
            .returning(Article)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
