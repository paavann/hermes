import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from hermes_api.db.enums import EventStatus


class ArticleResponse(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    published_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class EventResponse(BaseModel):
    id: uuid.UUID
    ai_headline: str
    category: str
    category_color: str
    location_name: Optional[str]
    trending_score: float
    article_count: int
    status: EventStatus
    first_reported_at: datetime
    last_updated_at: datetime
    has_lineage: bool = False
    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(EventResponse):
    ai_summary: str
    articles: list[ArticleResponse]
    has_lineage: bool = False


class MapEventResponse(BaseModel):
    id: uuid.UUID
    ai_headline: str
    category: str
    category_color: str
    location_name: Optional[str]
    latitude: float
    longitude: float
    trending_score: float
    article_count: int
    has_lineage: bool = False
    model_config = ConfigDict(from_attributes=True)


class LineageEdgeResponse(BaseModel):
    source_id: uuid.UUID
    target_id: uuid.UUID
    relationship_type: str
    model_config = ConfigDict(from_attributes=True)


class LineageNodeResponse(BaseModel):
    id: uuid.UUID
    ai_headline: str
    category: str
    category_color: str
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    trending_score: float
    article_count: int
    first_reported_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LineageGraphResponse(BaseModel):
    nodes: list[LineageNodeResponse]
    edges: list[LineageEdgeResponse]
