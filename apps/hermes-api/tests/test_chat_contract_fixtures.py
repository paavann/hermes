"""Contract tests for the shared chat JSON fixtures."""

from __future__ import annotations
import json
from pathlib import Path
import pytest
from pydantic import TypeAdapter
from hermes_api.schemas.chat import ChatRequest, ChatStreamEvent


FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "libs"
    / "shared"
    / "util-types"
    / "fixtures"
    / "chat"
)

REQUEST_FIXTURES = (
    ("request.json", "viewport"),
    ("request-event.json", "event"),
    ("request-global.json", "global"),
)

EVENT_FIXTURES = (
    "status.json",
    "token.json",
    "sources.json",
    "done.json",
    "error.json",
)


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("name", "scope_type"), REQUEST_FIXTURES)
def test_shared_chat_requests_validate(name: str, scope_type: str) -> None:
    request = ChatRequest.model_validate(_load(name))

    assert request.message
    assert request.scope.type == scope_type


@pytest.mark.parametrize("name", EVENT_FIXTURES)
def test_shared_sse_events_validate_and_round_trip(name: str) -> None:
    payload = _load(name)
    adapter: TypeAdapter[ChatStreamEvent] = TypeAdapter(ChatStreamEvent)

    event = adapter.validate_python(payload)

    assert event.type == name.removesuffix(".json")
    assert json.loads(event.model_dump_json()) == payload
