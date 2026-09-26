import uuid
from collections.abc import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_X, ST_Y, ST_MakeEnvelope, ST_Within
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from hermes_api.db.db import AsyncSessionLocal
from hermes_api.db.enums import EventStatus
from hermes_api.db.models.event import Event
from hermes_api.schemas.events import (
    EventDetailResponse,
    EventResponse,
    MapEventResponse,
)


router = APIRouter()


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/", response_model=list[EventResponse])
async def get_events(
    status: EventStatus | None = Query(
        EventStatus.ACTIVE, description="filter events by status."
    ),
    scope: EventStatus | None = Query(None, description="filter by event scope."),
    limit: int = Query(
        50, ge=1, le=200, description="maximum number of events to return."
    ),
    db: AsyncSession = Depends(get_db),
) -> list[EventResponse]:
    stmt = select(Event)
    if status:
        stmt = stmt.where(Event.status == status)
    if scope:
        stmt = stmt.where(Event.scope == scope)

    stmt = stmt.order_by(Event.trending_score.desc()).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()

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
    db: AsyncSession = Depends(get_db),
) -> list[MapEventResponse]:
    bbox_poly = ST_MakeEnvelope(west, south, east, north, 4326)
    stmt = (
        select(
            Event,
            ST_X(Event.location).label("longitude"),
            ST_Y(Event.location).label("latitude"),
        )
        .where(Event.location.isnot(None))
        .where(ST_Within(Event.location, bbox_poly))
        .where(Event.status == EventStatus.ACTIVE)
        .order_by(Event.trending_score.desc())
        .limit(200)
    )
    result = await db.execute(stmt)
    rows = result.all()
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
    event_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> EventDetailResponse:
    stmt = (
        select(Event).options(selectinload(Event.articles)).where(Event.id == event_id)
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="event not found.")

    return EventDetailResponse.model_validate(event, from_attributes=True)
