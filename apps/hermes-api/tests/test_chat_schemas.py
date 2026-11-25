"""Validation and JSON shape tests for chat schemas."""

import pytest
from pydantic import TypeAdapter, ValidationError
from hermes_api.schemas.chat import (
    ChatBoundingBox,
    ChatCoverage,
    ChatDoneEvent,
    ChatErrorEvent,
    ChatEventScope,
    ChatMapContext,
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
THREAD_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


def test_request_requires_message_and_thread_id() -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({})
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": "question"})


def test_request_rejects_malformed_thread_id() -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": "question", "thread_id": "not-a-uuid"})


def test_request_rejects_oversized_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 4001, thread_id=THREAD_ID)


def test_request_strips_and_rejects_blank_message() -> None:
    assert ChatRequest(message="  hello  ", thread_id=THREAD_ID).message == "hello"
    with pytest.raises(ValidationError, match="message must not be blank"):
        ChatRequest(message="   ", thread_id=THREAD_ID)


def test_request_defaults_to_optional_scope_context_and_no_retry() -> None:
    request = ChatRequest(message="question", thread_id=THREAD_ID)
    assert request.scope is None
    assert request.context is None
    assert request.retry is False


def test_request_accepts_map_context_without_explicit_scope() -> None:
    event_id = "3fa85f64-5717-4562-b3fc-2c963f66afa7"
    request = ChatRequest.model_validate(
        {
            "message": "what am i seeing on my screen?",
            "thread_id": THREAD_ID,
            "context": {
                "event_id": event_id,
                "bbox": {
                    "north": 45.0,
                    "south": 25.0,
                    "east": -70.0,
                    "west": -125.0,
                },
            },
        }
    )
    assert request.scope is None
    assert isinstance(request.context, ChatMapContext)
    assert str(request.context.event_id) == event_id
    assert request.context.bbox is not None
    assert request.context.bbox.west == -125.0


def test_request_accepts_retry() -> None:
    request = ChatRequest(message="question", thread_id=THREAD_ID, retry=True)
    assert request.retry is True


def test_event_scope_requires_event_id() -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(
            {
                "message": "question",
                "thread_id": THREAD_ID,
                "scope": {"type": "event"},
            }
        )


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
            "thread_id": THREAD_ID,
            "scope": {
                "type": "viewport",
                "bbox": {"north": 60, "south": 30, "east": 60, "west": 20},
            },
        }
    )
    event = ChatRequest.model_validate(
        {
            "message": "question",
            "thread_id": THREAD_ID,
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
            "thread_id": THREAD_ID,
            "scope": {
                "type": "viewport",
                "bbox": {"north": 60, "south": 30, "east": 60, "west": 20},
            },
        }
    )

    assert request.model_dump(mode="json") == {
        "message": "What changed?",
        "thread_id": THREAD_ID,
        "retry": False,
        "scope": {
            "type": "viewport",
            "bbox": {"north": 60.0, "south": 30.0, "east": 60.0, "west": 20.0},
        },
        "context": None,
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
