import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from hermes_db.enums import ThreadStatus
from hermes_db.services.thread import ThreadService
from hermes_db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_api.schemas.threads import (
    ThreadDetailResponse,
    ThreadEventResponse,
    ThreadResponse,
)


router = APIRouter()


async def get_thread_service(db: AsyncSession = Depends(get_db)) -> ThreadService:
    return ThreadService(db)


@router.get("/", response_model=list[ThreadResponse])
async def get_threads(
    status: ThreadStatus | None = Query(
        None, description="filter threads by status; defaults to active and dormant."
    ),
    limit: int = Query(
        50, ge=1, le=200, description="maximum number of threads to return."
    ),
    thread_service: ThreadService = Depends(get_thread_service),
) -> list[ThreadResponse]:
    statuses = (
        (status,) if status is not None else (ThreadStatus.ACTIVE, ThreadStatus.DORMANT)
    )
    threads = await thread_service.list_threads(statuses=statuses, limit=limit)
    return [ThreadResponse.model_validate(thread) for thread in threads]


@router.get("/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: uuid.UUID,
    thread_service: ThreadService = Depends(get_thread_service),
) -> ThreadDetailResponse:
    thread = await thread_service.get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found.")

    views = await thread_service.thread_events(thread_id)
    events = [
        ThreadEventResponse(
            id=view.id,
            ai_headline=view.ai_headline,
            ai_summary=view.ai_summary,
            category=view.category,
            category_color=view.category_color,
            impact_level=view.impact_level,
            importance_score=view.importance_score,
            verification_status=view.verification_status,
            location_name=view.location_name,
            latitude=view.latitude,
            longitude=view.longitude,
            first_reported_at=view.first_reported_at,
            last_updated_at=view.last_updated_at,
        )
        for view in views
    ]
    base = ThreadResponse.model_validate(thread)
    return ThreadDetailResponse(**base.model_dump(), events=events)
