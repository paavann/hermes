import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from hermes_api.db.enums import EventStatus




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
    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(EventResponse):
    ai_summary: str


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
    model_config = ConfigDict(from_attributes=True)