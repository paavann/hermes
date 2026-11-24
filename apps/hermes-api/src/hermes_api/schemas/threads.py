import uuid
from datetime import datetime
from hermes_db.enums import (
    ImpactLevel,
    ThreadKind,
    ThreadStatus,
    VerificationStatus,
)
from pydantic import BaseModel, ConfigDict


class ThreadResponse(BaseModel):
    id: uuid.UUID
    name: str
    kind: ThreadKind
    status: ThreadStatus
    description: str | None
    importance: float
    event_count: int
    started_at: datetime | None
    last_event_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class ThreadEventResponse(BaseModel):
    id: uuid.UUID
    ai_headline: str
    ai_summary: str | None
    category: str
    category_color: str
    impact_level: ImpactLevel
    importance_score: float
    verification_status: VerificationStatus
    location_name: str | None
    latitude: float | None
    longitude: float | None
    first_reported_at: datetime
    last_updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ThreadDetailResponse(ThreadResponse):
    events: list[ThreadEventResponse]
