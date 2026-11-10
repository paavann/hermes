from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatSourceKind(enum.StrEnum):
    EVENT = "event"
    ARTICLE = "article"
    TIMELINE = "timeline"
    WEB = "web"


class GroundingFlag(enum.StrEnum):
    MISSING_CITATIONS = "missing_citations"


class WebResult(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str
    source_name: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime
    snippet: str = Field(default="", max_length=1200)
    score: float | None = None


class ChatSource(BaseModel):
    kind: ChatSourceKind
    id: str
    event_id: uuid.UUID | None = None
    title: str
    url: str | None = None
    source_name: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_external: bool = False
    snippet: str | None = None
