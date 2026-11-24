from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import func, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import (
    ArticleCategory,
    ArticleCertainty,
    ArticleType,
    EventForm,
    EventScope,
    EventStatus,
    ImpactLevel,
    IngestStatus,
)
from hermes_db.models.article import Article
from hermes_db.models.article_label import ArticleLabel
from hermes_db.models.event import Event
from hermes_db.models.event_member import EventMember
from hermes_db.models.source import Source
from hermes_db.utils.datetime import ensure_utc


@dataclass(frozen=True, slots=True)
class AssignableArticle:
    """One analyzed article waiting for event assignment."""

    id: uuid.UUID
    title: str
    url: str
    feed_summary: str | None
    published_at: datetime | None
    source_id: uuid.UUID | None
    source_name: str | None
    source_slug: str | None
    source_origin_group: str | None
    family_id: uuid.UUID | None
    embedding: tuple[float, ...] | None
    embedding_model: str | None
    fact: str
    event_time: datetime | None
    article_type: ArticleType
    category: ArticleCategory
    event_form: EventForm | None
    specificity: int | None
    consequence: int | None
    certainty: ArticleCertainty | None
    severity: int | None
    scope: EventScope | None
    confidence: float | None
    entities: tuple[dict[str, object], ...]
    locations: tuple[dict[str, object], ...]

    @property
    def effective_time(self) -> datetime | None:
        return self.event_time or self.published_at


@dataclass(frozen=True, slots=True)
class EventCandidate:
    """An active event that can accept a new article."""

    id: uuid.UUID
    ai_headline: str
    ai_summary: str | None
    category: str
    scope: EventScope
    event_time: datetime | None
    latest_published_at: datetime | None
    country_code: str | None
    latitude: float | None
    longitude: float | None
    member_hash: str | None
    embedding: tuple[float, ...] | None
    embedding_model: str | None
    locations: tuple[dict[str, object], ...]
    entities: frozenset[str]
    event_form: EventForm | None


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
            ArticleLabel.event_time.label("event_time"),
            ArticleLabel.article_type.label("article_type"),
            ArticleLabel.category.label("category"),
            ArticleLabel.event_form.label("event_form"),
            ArticleLabel.specificity.label("specificity"),
            ArticleLabel.consequence.label("consequence"),
            ArticleLabel.certainty.label("certainty"),
            ArticleLabel.severity.label("severity"),
            ArticleLabel.scope.label("scope"),
            ArticleLabel.confidence.label("confidence"),
            ArticleLabel.entities.label("entities"),
            ArticleLabel.locations.label("locations"),
            rank,
        )
        .subquery("ranked_labels")
    )


def member_hash(article_ids: Sequence[uuid.UUID]) -> str:
    payload = "|".join(str(article_id) for article_id in sorted(article_ids))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class EventAssignmentService:
    """Candidate discovery and event creation for the cluster stage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def unclustered_articles(
        self,
        *,
        limit: int,
    ) -> list[AssignableArticle]:
        labels = _latest_label_subquery()
        order_time = func.coalesce(
            labels.c.event_time,
            Article.published_at,
            Article.ingested_at,
        )
        stmt = (
            select(
                Article.id,
                Article.title,
                Article.url,
                Article.feed_summary,
                Article.published_at,
                Article.source_id,
                Source.name,
                Source.slug,
                Source.origin_group,
                Article.family_id,
                Article.embedding,
                Article.embedding_model,
                labels.c.fact,
                labels.c.event_time,
                labels.c.article_type,
                labels.c.category,
                labels.c.event_form,
                labels.c.specificity,
                labels.c.consequence,
                labels.c.certainty,
                labels.c.severity,
                labels.c.scope,
                labels.c.confidence,
                labels.c.entities,
                labels.c.locations,
            )
            .join(Source, Source.id == Article.source_id, isouter=True)
            .join(labels, labels.c.article_id == Article.id)
            .where(Article.ingest_status == IngestStatus.LABELED)
            .where(Article.event_id.is_(None))
            .where(Article.reject_stage.is_(None))
            .where(labels.c.rank == 1)
            .where(labels.c.fact.is_not(None))
            .order_by(order_time, Article.id)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        articles: list[AssignableArticle] = []
        for row in rows:
            embedding: tuple[float, ...] | None = None
            if row.embedding is not None:
                embedding = tuple(float(value) for value in row.embedding)
            articles.append(
                AssignableArticle(
                    id=row.id,
                    title=row.title,
                    url=row.url,
                    feed_summary=row.feed_summary,
                    published_at=ensure_utc(row.published_at)
                    if row.published_at is not None
                    else None,
                    source_id=row.source_id,
                    source_name=row.name,
                    source_slug=row.slug,
                    source_origin_group=row.origin_group,
                    family_id=row.family_id,
                    embedding=embedding,
                    embedding_model=row.embedding_model,
                    fact=row.fact,
                    event_time=ensure_utc(row.event_time)
                    if row.event_time is not None
                    else None,
                    article_type=(
                        ArticleType(row.article_type)
                        if row.article_type is not None
                        else ArticleType.OTHER
                    ),
                    category=ArticleCategory(row.category)
                    if row.category is not None
                    else ArticleCategory.OTHER,
                    event_form=EventForm(row.event_form)
                    if row.event_form is not None
                    else None,
                    specificity=row.specificity,
                    consequence=row.consequence,
                    certainty=ArticleCertainty(row.certainty)
                    if row.certainty is not None
                    else None,
                    severity=row.severity,
                    scope=EventScope(row.scope) if row.scope is not None else None,
                    confidence=row.confidence,
                    entities=tuple(row.entities or ()),
                    locations=tuple(row.locations or ()),
                )
            )
        return articles

    async def candidates(
        self,
        article: AssignableArticle,
        *,
        since: datetime,
        ann_limit: int = 20,
        country_limit: int = 20,
        cap: int = 40,
    ) -> list[EventCandidate]:
        base = [
            Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]),
            Event.merged_into_id.is_(None),
            func.coalesce(Event.event_time, Event.latest_published_at) >= since,
        ]
        if article.embedding:
            distance = Event.embedding.cosine_distance(list(article.embedding))
        else:
            distance = None

        ann_stmt = select(Event.id).where(*base).where(Event.embedding.is_not(None))
        if distance is not None:
            ann_stmt = ann_stmt.order_by(distance)
        else:
            ann_stmt = ann_stmt.order_by(Event.last_updated_at.desc())
        ann_ids = ann_stmt.limit(ann_limit)

        country_code = self._article_country(article)
        id_queries = [ann_ids]
        if country_code is not None:
            country_stmt = (
                select(Event.id)
                .where(*base)
                .where(Event.country_code == country_code)
                .order_by(Event.last_updated_at.desc())
                .limit(country_limit)
            )
            id_queries.append(country_stmt)

        ids = union(*id_queries).subquery("candidate_ids")
        stmt = (
            select(
                Event.id,
                Event.ai_headline,
                Event.ai_summary,
                Event.category,
                Event.scope,
                Event.event_time,
                Event.latest_published_at,
                Event.country_code,
                ST_Y(Event.location).label("latitude"),
                ST_X(Event.location).label("longitude"),
                Event.member_hash,
                Event.embedding,
                Event.embedding_model,
                Event.locations,
            )
            .join(ids, ids.c.id == Event.id)
            .limit(cap)
        )
        rows = (await self._session.execute(stmt)).all()
        entities, forms = await self._candidate_signals([row.id for row in rows])
        candidates: list[EventCandidate] = []
        for row in rows:
            embedding: tuple[float, ...] | None = None
            if row.embedding is not None:
                embedding = tuple(float(value) for value in row.embedding)
            candidates.append(
                EventCandidate(
                    id=row.id,
                    ai_headline=row.ai_headline,
                    ai_summary=row.ai_summary,
                    category=row.category,
                    scope=EventScope(row.scope),
                    event_time=ensure_utc(row.event_time)
                    if row.event_time is not None
                    else None,
                    latest_published_at=ensure_utc(row.latest_published_at)
                    if row.latest_published_at is not None
                    else None,
                    country_code=row.country_code,
                    latitude=float(row.latitude)
                    if row.latitude is not None
                    else None,
                    longitude=float(row.longitude)
                    if row.longitude is not None
                    else None,
                    member_hash=row.member_hash,
                    embedding=embedding,
                    embedding_model=row.embedding_model,
                    locations=tuple(row.locations or ()),
                    entities=entities.get(row.id, frozenset()),
                    event_form=forms.get(row.id),
                )
            )
        return candidates

    async def _candidate_signals(
        self,
        event_ids: Sequence[uuid.UUID],
    ) -> tuple[dict[uuid.UUID, frozenset[str]], dict[uuid.UUID, EventForm]]:
        if not event_ids:
            return {}, {}
        stmt = (
            select(
                EventMember.event_id,
                ArticleLabel.entities,
                ArticleLabel.event_form,
            )
            .join(Article, Article.id == EventMember.article_id)
            .join(ArticleLabel, ArticleLabel.article_id == Article.id)
            .where(EventMember.event_id.in_(event_ids))
            .where(EventMember.is_current.is_(True))
        )
        grouped: dict[uuid.UUID, set[str]] = {event_id: set() for event_id in event_ids}
        form_counts: dict[uuid.UUID, dict[EventForm, int]] = {
            event_id: {} for event_id in event_ids
        }
        rows = (await self._session.execute(stmt)).all()
        for event_id, raw_entities, raw_form in rows:
            for entity in raw_entities or []:
                name = entity.get("name")
                if isinstance(name, str) and name.strip():
                    grouped[event_id].add(name.strip().casefold())
            if raw_form is not None:
                form = EventForm(raw_form)
                counts = form_counts[event_id]
                counts[form] = counts.get(form, 0) + 1
        forms: dict[uuid.UUID, EventForm] = {}
        for event_id, counts in form_counts.items():
            if counts:
                forms[event_id] = max(counts.items(), key=lambda item: item[1])[0]
        return {event_id: frozenset(names) for event_id, names in grouped.items()}, forms

    async def create_event(
        self,
        article: AssignableArticle,
        *,
        headline: str,
        summary: str,
        category: str,
        category_color: str,
        impact_level: ImpactLevel,
        scope: EventScope,
        latitude: float | None,
        longitude: float | None,
        location_name: str | None,
        country_code: str | None,
        first_reported_at: datetime,
        latest_published_at: datetime | None,
        now: datetime,
    ) -> Event:
        location = None
        if latitude is not None and longitude is not None:
            location = f"SRID=4326;POINT({longitude} {latitude})"
        event = Event(
            ai_headline=headline[:500],
            ai_summary=summary,
            category=category[:100],
            category_color=category_color[:7],
            impact_level=impact_level,
            scope=scope,
            location=location,
            location_name=location_name[:255] if location_name else None,
            country_code=country_code,
            event_time=article.effective_time,
            first_reported_at=first_reported_at,
            latest_published_at=latest_published_at,
            first_seen_at=now,
            last_updated_at=now,
            last_member_added_at=now,
            embedding=list(article.embedding) if article.embedding else None,
            embedding_model=article.embedding_model,
            # The describe stage owns this key; null means "describe me".
            member_hash=None,
            article_count=0,
            source_count=0,
            family_count=0,
            independent_origin_count=0,
            locations=[
                {
                    "name": location_name,
                    "country_code": country_code,
                }
            ]
            if location_name
            else [],
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def event_location(
        self,
        event_id: uuid.UUID,
    ) -> tuple[float | None, float | None, str | None]:
        stmt = select(
            ST_Y(Event.location),
            ST_X(Event.location),
            Event.location_name,
        ).where(Event.id == event_id)
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None, None, None
        return (
            float(row[0]) if row[0] is not None else None,
            float(row[1]) if row[1] is not None else None,
            row[2],
        )

    @staticmethod
    def _article_country(article: AssignableArticle) -> str | None:
        for location in article.locations:
            code = location.get("country_code")
            if isinstance(code, str) and len(code) == 2:
                return code.upper()
        return None

    @staticmethod
    def article_country(article: AssignableArticle) -> str | None:
        return EventAssignmentService._article_country(article)
