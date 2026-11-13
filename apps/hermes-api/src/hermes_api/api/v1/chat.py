from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from hermes_api.core.exceptions import ChatUnavailable
from hermes_api.schemas.chat import ChatRequest
from hermes_api.services.chat_service import ChatRuntime, ChatService


router = APIRouter()


def get_chat_service(request: Request) -> ChatService:
    runtime: ChatRuntime | None = getattr(request.app.state, "chat_runtime", None)
    if runtime is None:
        raise ChatUnavailable(
            "chat is disabled or model credentials are not configured."
        )
    return ChatService(runtime)


@router.post("", response_class=StreamingResponse)
async def create_chat_stream(
    payload: ChatRequest,
    request: Request,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    turn = await chat_service.prepare(request, payload)
    return StreamingResponse(
        chat_service.stream(turn, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
