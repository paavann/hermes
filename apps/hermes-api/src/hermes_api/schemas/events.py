import uuid
from datetime import datetime
from typing import Literal
from hermes_db.enums import (
    EventRelationshipType,
    EventScope,
    EventStatus,
    EventTlStatus,
    ImpactLevel,
    SelectionTier,
    VerificationStatus,
)
from pydantic import BaseModel, ConfigDict, Field


class ArticleResponse(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    published_at: datetime | None
    source_name: str | None = None
    model_config = ConfigDict(from_attributes=True)


EventActorKind = Literal["STATE", "ORGANIZATION", "PERSON", "GROUP"]
EventActorRole = Literal["ACTOR", "TARGET", "PARTICIPANT"]


class EventActorItem(BaseModel):
    name: str
    kind: EventActorKind
    role: EventActorRole
    location_name: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    model_config = ConfigDict(from_attributes=True)


class EventRelationshipItem(BaseModel):
    id: uuid.UUID
    relationship_type: EventRelationshipType
    direction: Literal["OUTGOING", "INCOMING"]
    confidence: float
    rationale: str
    related_event_id: uuid.UUID
    related_headline: str
    related_category: str
    related_category_color: str
    related_location_name: str | None
    related_latitude: float | None
    related_longitude: float | None
    related_importance_score: float
    related_event_time: datetime | None
    model_config = ConfigDict(from_attributes=True)


class MapRelationshipEdgeResponse(BaseModel):
    id: uuid.UUID
    source_event_id: uuid.UUID
    target_event_id: uuid.UUID
    source_headline: str
    source_category: str
    source_category_color: str
    source_location_name: str | None
    source_latitude: float
    source_longitude: float
    target_headline: str
    target_category: str
    target_category_color: str
    target_location_name: str | None
    target_latitude: float
    target_longitude: float
    relationship_type: EventRelationshipType
    confidence: float
    rationale: str
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
    relationship_count: int = 0
    actors: list[EventActorItem] = Field(default_factory=list)
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
    relationships: list[EventRelationshipItem] = Field(default_factory=list)


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
    relationship_count: int = 0
    actors: list[EventActorItem] = Field(default_factory=list)
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
