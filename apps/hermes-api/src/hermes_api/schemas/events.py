import uuid
from datetime import datetime
from hermes_db.enums import (
    EventScope,
    EventStatus,
    EventTlStatus,
    ImpactLevel,
    SelectionTier,
    VerificationStatus,
)
from pydantic import BaseModel, ConfigDict


class ArticleResponse(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    published_at: datetime | None
    source_name: str | None = None
    model_config = ConfigDict(from_attributes=True)


class EventResponse(BaseModel):
    id: uuid.UUID
    ai_headline: str
    category: str
    category_color: str
    location_name: str | None
    importance_score: float
    score_breakdown: dict[str, object]
    verification_status: VerificationStatus
    selection_tier: SelectionTier
    impact_level: ImpactLevel
    scope: EventScope
    article_count: int
    source_count: int
    family_count: int
    independent_origin_count: int
    thread_id: uuid.UUID | None
    thread_name: str | None = None
    status: EventStatus
    event_time: datetime | None
    first_reported_at: datetime
    last_updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(EventResponse):
    ai_summary: str
    articles: list[ArticleResponse]


class MapEventResponse(BaseModel):
    id: uuid.UUID
    ai_headline: str
    category: str
    category_color: str
    location_name: str | None
    latitude: float
    longitude: float
    importance_score: float
    verification_status: VerificationStatus
    selection_tier: SelectionTier
    impact_level: ImpactLevel
    scope: EventScope
    event_time: datetime | None
    article_count: int
    source_count: int
    family_count: int
    independent_origin_count: int
    thread_id: uuid.UUID | None
    thread_name: str | None = None
    model_config = ConfigDict(from_attributes=True)


class TlNodeResponse(BaseModel):
    id: str
    date: str
    headline: str
    summary: str
    location_name: str | None
    latitude: float | None
    longitude: float | None
    category_color: str | None = None


class TlEdgeResponse(BaseModel):
    source_node_id: str
    target_node_id: str
    relationship: str


class TlResponse(BaseModel):
    status: EventTlStatus
    message: str | None = None
    nodes: list[TlNodeResponse] = []
    edges: list[TlEdgeResponse] = []
    tl_summary: str = ""
    generated_at: datetime | None = None
