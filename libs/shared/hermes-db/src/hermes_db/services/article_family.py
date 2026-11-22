from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.models.article import Article
from hermes_db.models.article_family import ArticleFamily


@dataclass(frozen=True, slots=True)
class FamilyCandidate:
    family_id: uuid.UUID
    representative_article_id: uuid.UUID | None
    title_simhash: str
    body_simhash: str | None
    origin_group: str
    representative_time: datetime | None
    representative_embedding: tuple[float, ...] | None


class ArticleFamilyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recent_candidates(
        self,
        *,
        since: datetime,
        limit: int,
    ) -> list[FamilyCandidate]:
        representative_time = func.coalesce(
            Article.published_at,
            ArticleFamily.created_at,
        ).label("representative_time")
        stmt = (
            select(
                ArticleFamily.id,
                ArticleFamily.representative_article_id,
                ArticleFamily.title_simhash,
                ArticleFamily.body_simhash,
                ArticleFamily.primary_origin_group,
                representative_time,
                Article.embedding,
            )
            .join(
                Article,
                Article.id == ArticleFamily.representative_article_id,
                isouter=True,
            )
            .where(ArticleFamily.updated_at >= since)
            .order_by(ArticleFamily.updated_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        candidates: list[FamilyCandidate] = []
        for row in rows:
            embedding: tuple[float, ...] | None = None
            if row.embedding is not None:
                embedding = tuple(float(value) for value in row.embedding)
            candidates.append(
                FamilyCandidate(
                    family_id=row.id,
                    representative_article_id=row.representative_article_id,
                    title_simhash=row.title_simhash,
                    body_simhash=row.body_simhash,
                    origin_group=row.primary_origin_group,
                    representative_time=row.representative_time,
                    representative_embedding=embedding,
                )
            )
        return candidates

    async def create(
        self,
        *,
        article_id: uuid.UUID,
        title_simhash: str,
        body_simhash: str | None,
        origin_group: str,
    ) -> uuid.UUID:
        family = ArticleFamily(
            id=uuid.uuid4(),
            representative_article_id=article_id,
            title_simhash=title_simhash,
            body_simhash=body_simhash,
            primary_origin_group=origin_group,
            member_count=1,
        )
        self._session.add(family)
        await self._session.flush()
        family_id = family.id
        await self._session.execute(
            update(Article)
            .where(Article.id == article_id)
            .values(family_id=family_id)
            .execution_options(synchronize_session=False)
        )
        return family_id

    async def add_member(
        self,
        *,
        family_id: uuid.UUID,
        article_id: uuid.UUID,
        title_simhash: str,
        body_simhash: str | None,
        origin_group: str,
        adopt_representative: bool = False,
    ) -> None:
        values: dict[str, object] = {
            "member_count": ArticleFamily.member_count + 1,
        }
        if adopt_representative:
            values.update(
                {
                    "representative_article_id": article_id,
                    "title_simhash": title_simhash,
                    "body_simhash": body_simhash,
                    "primary_origin_group": origin_group,
                }
            )
        await self._session.execute(
            update(ArticleFamily)
            .where(ArticleFamily.id == family_id)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(
            update(Article)
            .where(Article.id == article_id)
            .values(family_id=family_id)
            .execution_options(synchronize_session=False)
        )

    async def list_for_articles(
        self,
        article_ids: Sequence[uuid.UUID],
    ) -> list[ArticleFamily]:
        if not article_ids:
            return []
        stmt = select(ArticleFamily).join(
            Article,
            Article.family_id == ArticleFamily.id,
        ).where(Article.id.in_(article_ids))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
