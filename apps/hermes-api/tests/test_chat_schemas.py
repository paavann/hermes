"""Validation and JSON shape tests for chat schemas."""

import pytest
from pydantic import TypeAdapter, ValidationError
from hermes_api.schemas.chat import (
    ChatBoundingBox,
    ChatCoverage,
    ChatDoneEvent,
    ChatErrorEvent,
    ChatEventScope,
    ChatGlobalScope,
    ChatHistoryMessage,
    ChatProvenance,
    ChatRequest,
    ChatSource,
    ChatSourcesEvent,
    ChatStatusEvent,
    ChatStreamEvent,
    ChatTokenEvent,
    ChatUsage,
    ChatViewportScope,
)


STREAM_EVENT = TypeAdapter(ChatStreamEvent)


def test_request_requires_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({})


def test_request_rejects_bad_role() -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(
            {
                "message": "question",
                "history": [{"role": "system", "content": "bad"}],
            }
        )


def test_request_rejects_oversized_message_and_history_content() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 4001)
    with pytest.raises(ValidationError):
        ChatHistoryMessage(role="user", content="x" * 8001)


def test_request_rejects_more_than_sixteen_messages() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            message="question",
            history=[
                {"role": "user", "content": f"turn {index}"} for index in range(17)
            ],
        )


def test_request_strips_and_rejects_blank_message() -> None:
    assert ChatRequest(message="  hello  ").message == "hello"
    with pytest.raises(ValidationError, match="message must not be blank"):
        ChatRequest(message="   ")


def test_request_defaults_to_global_scope() -> None:
    request = ChatRequest(message="question")
    assert isinstance(request.scope, ChatGlobalScope)


def test_event_scope_requires_event_id() -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": "question", "scope": {"type": "event"}})


def test_viewport_scope_requires_valid_box() -> None:
    with pytest.raises(ValidationError):
        ChatViewportScope.model_validate({"type": "viewport"})
    with pytest.raises(ValidationError, match="north must be greater"):
        ChatViewportScope(
            bbox=ChatBoundingBox(north=10.0, south=20.0, east=30.0, west=-30.0)
        )
    with pytest.raises(ValidationError, match="latitudes must be within"):
        ChatBoundingBox(north=91.0, south=0.0, east=30.0, west=-30.0)
    with pytest.raises(ValidationError, match="longitudes must be within"):
        ChatBoundingBox(north=10.0, south=0.0, east=181.0, west=-30.0)


def test_discriminated_scope_parses_each_variant() -> None:
    viewport = ChatRequest.model_validate(
        {
            "message": "question",
            "scope": {
                "type": "viewport",
                "bbox": {"north": 60, "south": 30, "east": 60, "west": 20},
            },
        }
    )
    event = ChatRequest.model_validate(
        {
            "message": "question",
            "scope": {
                "type": "event",
                "event_id": "00000000-0000-0000-0000-000000000001",
            },
        }
    )

    assert isinstance(viewport.scope, ChatViewportScope)
    assert isinstance(event.scope, ChatEventScope)


def test_request_json_snapshot() -> None:
    request = ChatRequest.model_validate(
        {
            "message": "What changed?",
            "history": [{"role": "user", "content": "Earlier question."}],
            "scope": {
                "type": "viewport",
                "bbox": {"north": 60, "south": 30, "east": 60, "west": 20},
            },
        }
    )

    assert request.model_dump(mode="json") == {
        "message": "What changed?",
        "history": [{"role": "user", "content": "Earlier question."}],
        "scope": {
            "type": "viewport",
            "bbox": {"north": 60.0, "south": 30.0, "east": 60.0, "west": 20.0},
        },
    }


def test_source_event_shape_parses() -> None:
    source = ChatSource.model_validate(
        {
            "kind": "event",
            "id": "00000000-0000-0000-0000-000000000001",
            "event_id": "00000000-0000-0000-0000-000000000001",
            "title": "Flooding",
            "latitude": 39.47,
            "longitude": -0.37,
            "is_external": False,
        }
    )

    assert source.kind == "event"
    assert source.url is None


def test_done_and_error_event_snapshots() -> None:
    done = ChatDoneEvent(
        provenance=ChatProvenance(events=1, articles=1, background=True),
        coverage=ChatCoverage(level="sufficient", result_count=1),
        usage=ChatUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        web_used=False,
        degraded=["semantic_unavailable"],
    )
    error = ChatErrorEvent(code="MODEL_TIMEOUT", message="timeout", retryable=True)

    assert done.model_dump(mode="json") == {
        "type": "done",
        "provenance": {
            "events": 1,
            "articles": 1,
            "timeline_nodes": 0,
            "web": 0,
            "background": True,
            "grounding": [],
        },
        "coverage": {
            "level": "sufficient",
            "result_count": 1,
            "best_semantic_similarity": None,
            "best_lexical_rank": None,
            "newest_age_hours": None,
            "recency_stale": False,
        },
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
        "web_used": False,
        "degraded": ["semantic_unavailable"],
    }
    assert error.model_dump(mode="json") == {
        "type": "error",
        "code": "MODEL_TIMEOUT",
        "message": "timeout",
        "retryable": True,
    }


def test_stream_event_union_discriminates_by_type() -> None:
    status = STREAM_EVENT.validate_python({"type": "status", "stage": "retrieving"})
    token = STREAM_EVENT.validate_python({"type": "token", "text": "hi"})
    sources = STREAM_EVENT.validate_python(
        {
            "type": "sources",
            "sources": [
                {
                    "kind": "web",
                    "id": "https://example.com",
                    "title": "Report",
                    "url": "https://example.com",
                    "is_external": True,
                }
            ],
        }
    )

    assert isinstance(status, ChatStatusEvent)
    assert isinstance(token, ChatTokenEvent)
    assert isinstance(sources, ChatSourcesEvent)
    assert sources.sources[0].kind == "web"
