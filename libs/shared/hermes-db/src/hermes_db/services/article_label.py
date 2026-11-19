import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.models.article_label import ArticleLabel
from hermes_db.protocols import ArticleLabelData
from hermes_db.utils.datetime import ensure_utc


class ArticleLabelService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_label(
        self,
        article_id: uuid.UUID,
        prompt_version: str,
    ) -> ArticleLabel | None:
        stmt = (
            select(ArticleLabel)
            .where(ArticleLabel.article_id == article_id)
            .where(ArticleLabel.prompt_version == prompt_version)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_label(self, article_id: uuid.UUID, prompt_version: str) -> bool:
        stmt = (
            select(ArticleLabel.id)
            .where(ArticleLabel.article_id == article_id)
            .where(ArticleLabel.prompt_version == prompt_version)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def upsert_label(
        self,
        article_id: uuid.UUID,
        prompt_version: str,
        model: str,
        label: ArticleLabelData,
    ) -> ArticleLabel | None:
        values = {
            "article_id": article_id,
            "prompt_version": prompt_version,
            "model": model,
            "is_event": label.is_event,
            "article_type": label.article_type,
            "event_time": (
                ensure_utc(label.event_time) if label.event_time is not None else None
            ),
            "severity": label.severity,
            "scope": label.scope,
            "confidence": label.confidence,
            "fact": label.fact,
            "scale_facts": label.scale_facts,
            "category": label.category,
            "event_form": label.event_form,
            "specificity": label.specificity,
            "consequence": label.consequence,
            "certainty": label.certainty,
            "reject_reason": label.reject_reason,
            "input_hash": label.input_hash,
            "evidence_quote": label.evidence_quote,
            "entities": label.entities,
            "locations": label.locations,
            "labeled_at": func.now(),
        }
        stmt = (
            pg_insert(ArticleLabel)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_article_labels_article_prompt",
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in {"article_id", "prompt_version"}
                },
            )
            .returning(ArticleLabel)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_labels(
        self,
        article_ids: Sequence[uuid.UUID],
        prompt_version: str,
    ) -> list[ArticleLabel]:
        if not article_ids:
            return []
        stmt = (
            select(ArticleLabel)
            .where(ArticleLabel.article_id.in_(article_ids))
            .where(ArticleLabel.prompt_version == prompt_version)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
