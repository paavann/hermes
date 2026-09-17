import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.db.db import get_db
from hermes_api.schemas.events import TlResponse
from hermes_api.services.tl_service import TlService

router = APIRouter()


@router.post("/{event_id}/tl", response_model=TlResponse)
async def analyze_event_tl(
    event_id: uuid.UUID,
    force_refresh: bool = Query(
        False, description="Bypass cache and force regeneration."
    ),
    db: AsyncSession = Depends(get_db),
) -> TlResponse:
    try:
        service = TlService(db)
        return await service.gen_tl(event_id, force_refresh=force_refresh)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Event not found.") from e
        raise HTTPException(status_code=500, detail=str(e)) from e