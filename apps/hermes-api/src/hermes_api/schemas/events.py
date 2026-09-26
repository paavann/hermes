import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from hermes_api.db.enums import EventStatus, EventTlStatus


class ArticleResponse(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    published_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class EventResponse(BaseModel):
    id: uuid.UUID
    ai_headline: str
    category: str
    category_color: str
    location_name: str | None
    trending_score: float
    article_count: int
    status: EventStatus
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
    trending_score: float
    article_count: int
    model_config = ConfigDict(from_attributes=True)


class TlNodeResponse(BaseModel):
    id: str
    date: str
    headline: str
    summary: str
    location_name: str | None
    latitude: float | None
    longitude: float | None
    # Only set for the terminal "current event" node; None for historical Wikipedia nodes.
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
