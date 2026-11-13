import logging
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from hermes_ai import GeocodingService
from hermes_db.services import GeocodeCacheService
from hermes_db.services.tl import EventTlService
from hermes_db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from hermes_api.schemas.events import TlResponse
from hermes_api.services.ai_service import AiService
from hermes_api.services.tl_service import TlService


logger = logging.getLogger(__name__)
router = APIRouter()


async def get_tl_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TlService:
    ai_service: AiService | None = getattr(request.app.state, "ai_service", None)
    if ai_service is None or not ai_service.has_extractor:
        logger.error("timeline service is unavailable due to missing credentials.")
        raise HTTPException(
            status_code=503,
            detail="Timeline synthesis service is unavailable due to missing credentials.",
        )
    tl_db = EventTlService(db)
    cache_service = GeocodeCacheService(db)
    geocoding = GeocodingService(cache_service)
    return TlService(tl_db, geocoding, ai=ai_service)


@router.post("/{event_id}", response_model=TlResponse)
async def analyze_event_tl(
    event_id: Annotated[
        uuid.UUID,
        Path(description="The unique identifier (UUID) of the target event."),
    ],
    force_refresh: Annotated[
        bool, Query(description="Bypass cache and force regeneration.")
    ] = False,
    tl_service: TlService = Depends(get_tl_service),
) -> TlResponse:
    return await tl_service.gen_tl(event_id, force_refresh=force_refresh)
