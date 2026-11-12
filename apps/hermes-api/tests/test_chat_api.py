"""Route-level tests for the chat SSE endpoint."""

from __future__ import annotations
from collections.abc import AsyncIterator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hermes_api.api.v1.chat import get_chat_service, router
from hermes_api.core.errors import register_err_handlers
from hermes_api.core.exceptions import (
    ChatRateLimitExceeded,
)


class FakeChatService:
    def __init__(
        self,
        *,
        prepare_error: Exception | None = None,
        frames: tuple[str, ...] = (),
    ) -> None:
        self.prepare_error = prepare_error
        self.frames = frames
        self.prepared = 0

    async def prepare(self, request: object, payload: object) -> object:
        if self.prepare_error is not None:
            raise self.prepare_error
        self.prepared += 1
        return "turn"

    async def stream(self, turn: object, request: object) -> AsyncIterator[str]:
        for frame in self.frames:
            yield frame


def _app(service: FakeChatService | None = None) -> FastAPI:
    app = FastAPI()
    register_err_handlers(app)
    app.include_router(router, prefix="/api/v1/chat")
    if service is not None:
        app.dependency_overrides[get_chat_service] = lambda: service
    return app


def test_chat_route_rejects_invalid_body_with_422() -> None:
    with TestClient(_app(FakeChatService())) as client:
        response = client.post("/api/v1/chat", json={"message": ""})

    assert response.status_code == 422
    assert response.json()["err_code"] == "VALIDATION_ERROR"


def test_chat_route_rejects_malformed_bbox() -> None:
    with TestClient(_app(FakeChatService())) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "flooding",
                "scope": {
                    "type": "viewport",
                    "bbox": {
                        "north": 10,
                        "south": 20,
                        "east": 0,
                        "west": 0,
                    },
                },
            },
        )

    assert response.status_code == 422


def test_chat_route_returns_429_with_retry_after() -> None:
    service = FakeChatService(prepare_error=ChatRateLimitExceeded(30, limit=10))
    with TestClient(_app(service)) as client:
        response = client.post("/api/v1/chat", json={"message": "question"})

    assert response.status_code == 429
    assert response.json()["err_code"] == "CHAT_RATE_LIMIT_EXCEEDED"
    assert response.headers["retry-after"] == "30"


def test_chat_route_is_503_when_runtime_is_missing() -> None:
    with TestClient(_app()) as client:
        response = client.post("/api/v1/chat", json={"message": "question"})

    assert response.status_code == 503
    assert response.json()["err_code"] == "CHAT_UNAVAILABLE"


def test_chat_route_streams_events_in_order() -> None:
    frames = (
        'event: status\ndata: {"type":"status","stage":"accepted"}\n\n',
        'event: token\ndata: {"type":"token","text":"Hello"}\n\n',
        'event: sources\ndata: {"type":"sources","sources":[]}\n\n',
        'event: done\ndata: {"type":"done","provenance":{"events":0},'
        '"coverage":{"level":"empty"},"usage":null,"web_used":false,'
        '"degraded":[]}\n\n',
    )
    service = FakeChatService(frames=frames)

    with (
        TestClient(_app(service)) as client,
        client.stream("POST", "/api/v1/chat", json={"message": "question"}) as response,
    ):
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    names = [
        line.removeprefix("event: ")
        for line in body.splitlines()
        if line.startswith("event: ")
    ]
    assert names == ["status", "token", "sources", "done"]
    assert service.prepared == 1
