import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from hermes_db.enums import EventScope, EventStatus
from hermes_db.models.event import Event
from hermes_db.services.event import EventService
from hermes_db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_api.schemas.events import (
    ArticleResponse,
    EventDetailResponse,
    EventResponse,
    MapEventResponse,
)


router = APIRouter()


async def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(db)


def _event_response(event: Event) -> EventResponse:
    thread_name = event.thread.name if event.thread is not None else None
    return EventResponse(
        id=event.id,
        ai_headline=event.ai_headline,
        category=event.category,
        category_color=event.category_color,
        location_name=event.location_name,
        importance_score=event.importance_score,
        score_breakdown=event.score_breakdown,
        verification_status=event.verification_status,
        selection_tier=event.selection_tier,
        impact_level=event.impact_level,
        scope=event.scope,
        article_count=event.article_count,
        source_count=event.source_count,
        family_count=event.family_count,
        independent_origin_count=event.independent_origin_count,
        thread_id=event.thread_id,
        thread_name=thread_name,
        status=event.status,
        event_time=event.event_time,
        first_reported_at=event.first_reported_at,
        last_updated_at=event.last_updated_at,
    )


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
    return [_event_response(event) for event in events]


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
            importance_score=row.Event.importance_score,
            verification_status=row.Event.verification_status,
            selection_tier=row.Event.selection_tier,
            impact_level=row.Event.impact_level,
            scope=row.Event.scope,
            event_time=row.Event.event_time,
            article_count=row.Event.article_count,
            source_count=row.Event.source_count,
            family_count=row.Event.family_count,
            independent_origin_count=row.Event.independent_origin_count,
            thread_id=row.Event.thread_id,
            thread_name=row.thread_name,
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
    base = _event_response(event)
    articles = [
        ArticleResponse(
            id=article.id,
            title=article.title,
            url=article.url,
            published_at=article.published_at,
            source_name=article.source.name if article.source is not None else None,
        )
        for article in sorted(
            event.articles,
            key=lambda item: item.published_at or event.first_reported_at,
            reverse=True,
        )[:50]
    ]
    return EventDetailResponse(
        **base.model_dump(),
        ai_summary=event.ai_summary or "",
        articles=articles,
    )
