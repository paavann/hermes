import uuid
from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_X, ST_Y, ST_MakeEnvelope, ST_Within
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hermes_api.db.db import AsyncSessionLocal
from hermes_api.db.enums import EventStatus
from hermes_api.db.models.event import Event
from hermes_api.db.models.event_edge import EventEdge
from hermes_api.db.models.story_allowlist import StoryAllowlist
from hermes_api.schemas.events import (
    EventDetailResponse,
    EventResponse,
    LineageEdgeResponse,
    LineageGraphResponse,
    LineageNodeResponse,
    MapEventResponse,
)

router = APIRouter()





async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session



@router.get("/", response_model=list[EventResponse])
async def get_events(
    status: Optional[EventStatus] = Query(EventStatus.ACTIVE, description="filter events by status."),
    scope: Optional[EventStatus] = Query(None, description="filter by event scope."),
    limit: int = Query(50, ge=1, le=200, description="maximum number of events to return."),
    db: AsyncSession = Depends(get_db)
) -> list[EventResponse]:
    stmt = select(
        Event,
        select(StoryAllowlist.id).where(StoryAllowlist.event_id == Event.id).exists().label("has_lineage")
    )
    if status:
        stmt = stmt.where(Event.status==status)
    if scope:
        stmt = stmt.where(Event.scope==scope)
    
    stmt = stmt.order_by(Event.trending_score.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()
    
    events = []
    for row in rows:
        event, has_lineage = row
        event.has_lineage = has_lineage
        events.append(event)
        
    return [EventResponse.model_validate(e) for e in events]



@router.get("/bbox", response_model=list[MapEventResponse])
async def get_events_by_bbox(
    north: float = Query(..., ge=-90, le=90, description="northern latitude boundary."),
    south: float = Query(..., ge=-90, le=90, description="southern latitude boundary."),
    east: float = Query(..., ge=-180, le=180, description="eastern longitude boundary."),
    west: float = Query(..., ge=-180, le=180, description="western longitude boundary."),
    db: AsyncSession = Depends(get_db)
) -> list[MapEventResponse]:
    bbox_poly = ST_MakeEnvelope(west, south, east, north, 4326)
    stmt = (
        select(
            Event,
            ST_X(Event.location).label("longitude"),
            ST_Y(Event.location).label("latitude"),
            select(StoryAllowlist.id).where(StoryAllowlist.event_id == Event.id).exists().label("has_lineage"),
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
            has_lineage=row.has_lineage,
        )
        for row in rows
    ]



@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(event_id: uuid.UUID, db: AsyncSession=Depends(get_db)) -> EventDetailResponse:
    stmt = (
        select(
            Event,
            select(StoryAllowlist.id).where(StoryAllowlist.event_id == Event.id).exists().label("has_lineage")
        )
        .options(selectinload(Event.articles))
        .where(Event.id==event_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="event not found.")
    
    event, has_lineage = row
    event.has_lineage = has_lineage
    return event





@router.get("/{event_id}/lineage", response_model=LineageGraphResponse)
async def get_event_lineage(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> LineageGraphResponse:
    # 1. Walk the graph backward using a recursive CTE with cycle protection
    query = text("""
        WITH RECURSIVE lineage_cte AS (
            -- Anchor: start with the requested event
            SELECT 
                id, 
                first_reported_at, 
                ARRAY[id] as path
            FROM events
            WHERE id = :start_id

            UNION ALL

            -- Recursive step: find related events through edges
            SELECT 
                e.id, 
                e.first_reported_at, 
                cte.path || e.id
            FROM events e
            JOIN event_edges ee ON (e.id = ee.event_a_id OR e.id = ee.event_b_id)
            JOIN lineage_cte cte ON (cte.id = ee.event_a_id OR cte.id = ee.event_b_id)
            WHERE e.id != cte.id
              AND e.first_reported_at <= cte.first_reported_at
              AND NOT (e.id = ANY(cte.path))
        )
        SELECT DISTINCT id FROM lineage_cte;
    """)
    result = await db.execute(query, {"start_id": event_id})
    node_ids = [row.id for row in result.all()]
    
    if not node_ids:
        # If the start_id itself didn't exist, node_ids will be empty
        raise HTTPException(status_code=404, detail="event not found or no lineage available.")

    # 2. Fetch all nodes with spatial decomposition
    nodes_stmt = (
        select(
            Event,
            ST_X(Event.location).label("longitude"),
            ST_Y(Event.location).label("latitude")
        )
        .where(Event.id.in_(node_ids))
        .order_by(Event.first_reported_at.asc())
    )
    nodes_result = await db.execute(nodes_stmt)
    node_rows = nodes_result.all()
    
    nodes = []
    for row in node_rows:
        nodes.append(LineageNodeResponse(
            id=row.Event.id,
            ai_headline=row.Event.ai_headline,
            category=row.Event.category,
            category_color=row.Event.category_color,
            location_name=row.Event.location_name,
            latitude=row.latitude,
            longitude=row.longitude,
            trending_score=row.Event.trending_score,
            article_count=row.Event.article_count,
            first_reported_at=row.Event.first_reported_at
        ))
        
    # 3. Fetch all edges connecting these nodes
    edges_stmt = select(EventEdge).where(
        EventEdge.event_a_id.in_(node_ids),
        EventEdge.event_b_id.in_(node_ids)
    )
    edges_result = await db.execute(edges_stmt)
    edges = [
        LineageEdgeResponse(
            source_id=edge.event_a_id,
            target_id=edge.event_b_id,
            relationship_type=edge.relationship_type
        )
        for edge in edges_result.scalars().all()
    ]

    return LineageGraphResponse(nodes=nodes, edges=edges)