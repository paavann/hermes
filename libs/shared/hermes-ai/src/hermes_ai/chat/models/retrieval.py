from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator


class CoverageLevel(enum.StrEnum):
    EMPTY = "empty"
    THIN = "thin"
    SUFFICIENT = "sufficient"


class DegradedFlag(enum.StrEnum):
    PLANNER_FALLBACK = "planner_fallback"
    SEMANTIC_UNAVAILABLE = "semantic_unavailable"
    WEB_UNAVAILABLE = "web_unavailable"
    MISSING_CITATIONS = "missing_citations"


class RetrievalFilters(BaseModel):
    category: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> Self:
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be before or equal to end.")
        return self


class RetrievedArticle(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    title: str
    url: str
    source_name: str | None = None
    published_at: datetime | None = None


class RetrievedTimelineNode(BaseModel):
    id: str
    date: str
    headline: str
    summary: str
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    category_color: str | None = None


class RetrievedTimelineEdge(BaseModel):
    source_node_id: str
    target_node_id: str
    relationship: str


class RetrievedTimeline(BaseModel):
    summary: str = ""
    nodes: list[RetrievedTimelineNode] = Field(default_factory=list)
    edges: list[RetrievedTimelineEdge] = Field(default_factory=list)


class RetrievedEvidence(BaseModel):
    event_id: uuid.UUID
    headline: str
    summary: str | None = None
    category: str
    category_color: str | None = None
    impact_level: str
    status: str
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    first_reported_at: datetime
    last_updated_at: datetime
    age_hours: float = 0.0
    trending_score: float = 0.0
    lexical_rank: int | None = None
    semantic_similarity: float | None = None
    rrf: float = 0.0
    articles: list[RetrievedArticle] = Field(default_factory=list)
    timeline: RetrievedTimeline | None = None


class Coverage(BaseModel):
    level: CoverageLevel
    result_count: int = 0
    best_semantic_similarity: float | None = None
    best_lexical_rank: int | None = None
    newest_age_hours: float | None = None
    recency_stale: bool = False


class RetrievalResult(BaseModel):
    evidence: list[RetrievedEvidence] = Field(default_factory=list)
    coverage: Coverage
    degraded: list[DegradedFlag] = Field(default_factory=list)
