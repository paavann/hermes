from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hermes_db.enums import (
    ArticleBodySource,
    IngestStatus,
    RejectStage,
    SourceFetchPolicy,
)
from hermes_db.models.article import Article


@dataclass(frozen=True, slots=True)
class AnalysisArticle:
    """Article snapshot consumed by the analyze stage.

    The snapshot deliberately carries the source policy so the stage can decide
    whether a transient body fetch is allowed without keeping a session open
    across network calls.
    """

    id: uuid.UUID
    title: str
    url: str
    feed_summary: str | None
    published_at: datetime | None
    language: str | None
    attempt_count: int
    family_id: uuid.UUID | None
    source_name: str | None
    source_slug: str | None
    source_origin_group: str | None
    fetch_policy: SourceFetchPolicy
    paywall: bool


class ArticleAnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_for_analysis(
        self,
        article_ids: Sequence[uuid.UUID],
    ) -> list[AnalysisArticle]:
        if not article_ids:
            return []
        stmt = (
            select(Article)
            .where(Article.id.in_(article_ids))
            .options(selectinload(Article.source))
        )
        result = await self._session.execute(stmt)
        snapshots: list[AnalysisArticle] = []
        for article in result.scalars().all():
            source = article.source
            snapshots.append(
                AnalysisArticle(
                    id=article.id,
                    title=article.title,
                    url=article.url,
                    feed_summary=article.feed_summary,
                    published_at=article.published_at,
                    language=article.language,
                    attempt_count=article.attempt_count,
                    family_id=article.family_id,
                    source_name=source.name if source else None,
                    source_slug=source.slug if source else None,
                    source_origin_group=source.origin_group if source else None,
                    fetch_policy=(
                        source.fetch_policy
                        if source
                        else SourceFetchPolicy.SUMMARY_ONLY
                    ),
                    paywall=source.paywall if source else True,
                )
            )
        return snapshots

    async def save_text(
        self,
        article_id: uuid.UUID,
        *,
        body_source: ArticleBodySource | None,
        body_simhash: str | None,
        title_simhash: str | None,
        word_count: int,
        input_quality: float,
        fetch_http_status: int | None,
    ) -> None:
        stmt = (
            update(Article)
            .where(Article.id == article_id)
            .values(
                body_source=body_source,
                body_simhash=body_simhash,
                title_simhash=title_simhash,
                word_count=word_count,
                input_quality=input_quality,
                fetch_http_status=fetch_http_status,
            )
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(stmt)

    async def save_embedding(
        self,
        article_id: uuid.UUID,
        *,
        model: str,
        embedding: Sequence[float],
        input_hash: str,
    ) -> None:
        stmt = (
            update(Article)
            .where(Article.id == article_id)
            .values(
                embedding=list(embedding),
                embedding_model=model,
                embedding_input_hash=input_hash,
            )
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(stmt)

    async def finalize(
        self,
        article_id: uuid.UUID,
        *,
        status: IngestStatus,
        reject_stage: RejectStage | None = None,
        reject_reason: str | None = None,
        error: str | None = None,
    ) -> None:
        rejected = status == IngestStatus.REJECTED
        stmt = (
            update(Article)
            .where(Article.id == article_id)
            .values(
                ingest_status=status,
                claimed_at=None,
                claimed_by=None,
                last_error=error,
                reject_stage=reject_stage if rejected else None,
                reject_reason=reject_reason if rejected else None,
                rejected_at=func.now() if rejected else None,
            )
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(stmt)
