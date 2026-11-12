"""Tests for chat exception responses and CORS header merging."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hermes_api.core.errors import register_err_handlers
from hermes_api.core.exceptions import (
    ChatBudgetExhausted,
    ChatBusy,
    ChatRateLimitExceeded,
    ChatUnavailable,
)


ORIGIN = "https://app.example.com"


def _client(exception: Exception) -> TestClient:
    app = FastAPI()
    register_err_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise exception

    return TestClient(app)


def test_rate_limit_response_has_retry_and_cors_headers() -> None:
    with _client(ChatRateLimitExceeded(42, limit=10)) as client:
        response = client.get("/boom", headers={"origin": ORIGIN})

    assert response.status_code == 429
    body = response.json()
    assert body["err_code"] == "CHAT_RATE_LIMIT_EXCEEDED"
    assert body["details"] == {"retry_after": 42}
    assert response.headers["retry-after"] == "42"
    assert response.headers["x-ratelimit-limit"] == "10"
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_budget_response_has_reset_headers() -> None:
    with _client(
        ChatBudgetExhausted(3600, limit=500_000, used=500_000, reserved=0)
    ) as client:
        response = client.get("/boom")

    assert response.status_code == 429
    assert response.json()["err_code"] == "CHAT_BUDGET_EXHAUSTED"
    assert response.headers["retry-after"] == "3600"
    assert response.headers["x-ratelimit-reset"] == "3600"


def test_unavailable_response_is_503() -> None:
    with _client(ChatUnavailable("missing chat credentials")) as client:
        response = client.get("/boom")

    assert response.status_code == 503
    body = response.json()
    assert body["err_code"] == "CHAT_UNAVAILABLE"
    assert body["details"] == {"reason": "missing chat credentials"}


def test_busy_response_is_503_with_retry_after() -> None:
    with _client(ChatBusy(2)) as client:
        response = client.get("/boom")

    assert response.status_code == 503
    assert response.json()["err_code"] == "CHAT_BUSY"
    assert response.headers["retry-after"] == "2"
