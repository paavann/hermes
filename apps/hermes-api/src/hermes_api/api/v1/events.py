import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from hermes_db.enums import EventScope, EventStatus
from hermes_db.models.event import Event
from hermes_db.services.event import EventService
from hermes_db.services.event_relationship import (
    EventRelationshipService,
    EventRelationshipView,
    MapRelationshipView,
)
from hermes_db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_api.schemas.events import (
    ArticleResponse,
    EventActorItem,
    EventDetailResponse,
    EventRelationshipItem,
    EventResponse,
    MapEventResponse,
    MapRelationshipEdgeResponse,
)


router = APIRouter()


async def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(db)


async def get_relationship_service(
    db: AsyncSession = Depends(get_db),
) -> EventRelationshipService:
    return EventRelationshipService(db)


_VALID_ACTOR_KINDS = frozenset({"STATE", "ORGANIZATION", "PERSON", "GROUP"})
_VALID_ACTOR_ROLES = frozenset({"ACTOR", "TARGET", "PARTICIPANT"})


def _optional_float(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _event_actors(raw_actors: object) -> list[EventActorItem]:
    if not isinstance(raw_actors, (list, tuple)):
        return []
    items: list[EventActorItem] = []
    for raw in raw_actors:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        kind = str(raw.get("kind") or "").upper()
        role = str(raw.get("role") or "").upper()
        if (
            not isinstance(name, str)
            or not name.strip()
            or kind not in _VALID_ACTOR_KINDS
            or role not in _VALID_ACTOR_ROLES
        ):
            continue
        loc_name = raw.get("location_name")
        cc = raw.get("country_code")
        items.append(
            EventActorItem(
                name=name.strip(),
                kind=kind,  # type: ignore[arg-type]
                role=role,  # type: ignore[arg-type]
                location_name=loc_name.strip() if isinstance(loc_name, str) and loc_name.strip() else None,
                country_code=cc.upper() if isinstance(cc, str) and len(cc) == 2 else None,
                latitude=_optional_float(raw.get("latitude")),
                longitude=_optional_float(raw.get("longitude")),
            )
        )
    return items


def _event_response(
    event: Event, *, relationship_count: int = 0
) -> EventResponse:
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
        relationship_count=relationship_count,
        actors=_event_actors(getattr(event, "actors", None)),
        thread_id=event.thread_id,
        thread_name=thread_name,
        status=event.status,
        event_time=event.event_time,
        first_reported_at=event.first_reported_at,
        last_updated_at=event.last_updated_at,
    )


def _relationship_item(rel: EventRelationshipView) -> EventRelationshipItem:
    return EventRelationshipItem(
        id=rel.id,
        relationship_type=rel.relationship_type,
        direction=rel.direction,
        confidence=rel.confidence,
        rationale=rel.rationale,
        related_event_id=rel.related_event_id,
        related_headline=rel.related_headline,
        related_category=rel.related_category,
        related_category_color=rel.related_category_color,
        related_location_name=rel.related_location_name,
        related_latitude=rel.related_latitude,
        related_longitude=rel.related_longitude,
        related_importance_score=rel.related_importance_score,
        related_event_time=rel.related_event_time,
    )


def _relationship_edge_response(
    edge: MapRelationshipView,
) -> MapRelationshipEdgeResponse:
    return MapRelationshipEdgeResponse(
        id=edge.id,
        source_event_id=edge.source_event_id,
        target_event_id=edge.target_event_id,
        source_headline=edge.source_headline,
        source_category=edge.source_category,
        source_category_color=edge.source_category_color,
        source_location_name=edge.source_location_name,
        source_latitude=edge.source_latitude,
        source_longitude=edge.source_longitude,
        target_headline=edge.target_headline,
        target_category=edge.target_category,
        target_category_color=edge.target_category_color,
        target_location_name=edge.target_location_name,
        target_latitude=edge.target_latitude,
        target_longitude=edge.target_longitude,
        relationship_type=edge.relationship_type,
        confidence=edge.confidence,
        rationale=edge.rationale,
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
    counts = await event_service.relationship_counts([event.id for event in events])
    return [
        _event_response(event, relationship_count=counts.get(event.id, 0))
        for event in events
    ]


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
    counts = await event_service.relationship_counts([row.Event.id for row in rows])
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
            relationship_count=counts.get(row.Event.id, 0),
            actors=_event_actors(getattr(row.Event, "actors", None)),
            thread_id=row.Event.thread_id,
            thread_name=row.thread_name,
        )
        for row in rows
    ]


@router.get("/relationships", response_model=list[MapRelationshipEdgeResponse])
async def get_relationships_by_bbox(
    north: float = Query(..., ge=-90, le=90, description="northern latitude boundary."),
    south: float = Query(..., ge=-90, le=90, description="southern latitude boundary."),
    east: float = Query(
        ..., ge=-180, le=180, description="eastern longitude boundary."
    ),
    west: float = Query(
        ..., ge=-180, le=180, description="western longitude boundary."
    ),
    limit: int = Query(
        400, ge=1, le=1000, description="maximum number of relationship edges to return."
    ),
    event_service: EventService = Depends(get_event_service),
    relationship_service: EventRelationshipService = Depends(
        get_relationship_service
    ),
) -> list[MapRelationshipEdgeResponse]:
    rows = await event_service.get_events_by_bbox(
        north=north, south=south, east=east, west=west
    )
    event_ids = [row.Event.id for row in rows]
    if not event_ids:
        return []
    edges = await relationship_service.relationships_for_event_ids(
        event_ids,
        limit=limit,
    )
    return [_relationship_edge_response(edge) for edge in edges]


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: uuid.UUID,
    event_service: EventService = Depends(get_event_service),
    relationship_service: EventRelationshipService = Depends(
        get_relationship_service
    ),
) -> EventDetailResponse:
    event = await event_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="event not found.")
    relationships = await relationship_service.relationships_for_event(event.id)
    relationship_items = [_relationship_item(rel) for rel in relationships]
    base = _event_response(event, relationship_count=len(relationship_items))
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
        relationships=relationship_items,
    )
