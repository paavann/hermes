from fastapi import APIRouter

from hermes_api.api.v1.events import router as events_router
from hermes_api.api.v1.tl import router as tl_router

api_router = APIRouter()

api_router.include_router(events_router, prefix="/events", tags=["events"])
api_router.include_router(tl_router, prefix="/events/tl", tags=["timeline"])
