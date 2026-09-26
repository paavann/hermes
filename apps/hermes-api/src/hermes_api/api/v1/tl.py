import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_api.db.db import get_db
from hermes_api.schemas.events import TlResponse
from hermes_api.services.tl_service import TlService


router = APIRouter()


@router.post("/{event_id}", response_model=TlResponse)
async def analyze_event_tl(
    event_id: Annotated[
        uuid.UUID,
        Path(description="The unique identifier (UUID) of the target event."),
    ],
    force_refresh: Annotated[
        bool, Query(description="Bypass cache and force regeneration.")
    ] = False,
    db: AsyncSession = Depends(get_db),
) -> TlResponse:
    return await TlService(db).gen_tl(event_id, force_refresh=force_refresh)
