import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from hermes_db.enums import EventScope, EventStatus
from hermes_db.services.event import EventService
from hermes_db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_api.schemas.events import (
    EventDetailResponse,
    EventResponse,
    MapEventResponse,
)


router = APIRouter()


async def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(db)


@router.get("/", response_model=list[EventResponse])
async def get_events(
    status: EventStatus | None = Query(
        EventStatus.ACTIVE, description="filter events by status."
    ),
    scope: EventScope | None = Query(None, description="filter by event scope."),
    limit: int = Query(
        50, ge=1, le=200, description="maximum number of events to return."
    ),
    event_service: EventService = Depends(get_event_service),
) -> list[EventResponse]:
    events = await event_service.get_events(status=status, scope=scope, limit=limit)
    return [EventResponse.model_validate(e) for e in events]


@router.get("/bbox", response_model=list[MapEventResponse])
async def get_events_by_bbox(
    north: float = Query(..., ge=-90, le=90, description="northern latitude boundary."),
    south: float = Query(..., ge=-90, le=90, description="southern latitude boundary."),
    east: float = Query(
        ..., ge=-180, le=180, description="eastern longitude boundary."
    ),
    west: float = Query(
        ..., ge=-180, le=180, description="western longitude boundary."
    ),
    event_service: EventService = Depends(get_event_service),
) -> list[MapEventResponse]:
    rows = await event_service.get_events_by_bbox(
        north=north, south=south, east=east, west=west
    )
    return [
        MapEventResponse(
            id=row.Event.id,
            ai_headline=row.Event.ai_headline,
            category=row.Event.category,
            category_color=row.Event.category_color,
            location_name=row.Event.location_name,
            latitude=row.latitude,
            longitude=row.longitude,
            trending_score=row.Event.trending_score,
            article_count=row.Event.article_count,
        )
        for row in rows
    ]


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: uuid.UUID, event_service: EventService = Depends(get_event_service)
) -> EventDetailResponse:
    event = await event_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="event not found.")
    else:
        return EventDetailResponse.model_validate(event, from_attributes=True)
