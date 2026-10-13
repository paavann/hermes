from fastapi import APIRouter
from hermes_api.api.v1.events import router as events_router
from hermes_api.api.v1.tl import router as tl_router
from hermes_api.schemas.errors import ErrorResponseSchema


standard_errors = {
    400: {"model": ErrorResponseSchema, "description": "Business Logic Error"},
    404: {"model": ErrorResponseSchema, "description": "Resource Not Found"},
    422: {"model": ErrorResponseSchema, "description": "Validation Error"},
    500: {"model": ErrorResponseSchema, "description": "Internal Server Error"},
}

api_router = APIRouter(responses=standard_errors)

api_router.include_router(events_router, prefix="/events", tags=["events"])
api_router.include_router(tl_router, prefix="/events/tl", tags=["timeline"])
