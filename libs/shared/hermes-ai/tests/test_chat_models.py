"""Validation tests for the internal chat contracts."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from hermes_ai.chat.models import (
    BoundingBox,
    ChatPlan,
    ChatScope,
    ChatSourceKind,
    ChatTurn,
    PlanTimeRange,
    ScopeType,
    WebResult,
)


def test_event_scope_requires_event_id() -> None:
    with pytest.raises(ValidationError, match="event scope requires event_id"):
        ChatScope(type=ScopeType.EVENT)


def test_viewport_scope_requires_bbox() -> None:
    with pytest.raises(ValidationError, match="viewport scope requires bbox"):
        ChatScope(type=ScopeType.VIEWPORT)


def test_global_scope_has_no_required_fields() -> None:
    scope = ChatScope(type=ScopeType.GLOBAL)
    assert scope.describe() == "all eligible plottings."


def test_event_scope_describe_includes_identifier() -> None:
    event_id = uuid.uuid4()
    scope = ChatScope(type=ScopeType.EVENT, event_id=event_id)
    assert str(event_id) in scope.describe()


def test_viewport_scope_describe_includes_bounds() -> None:
    scope = ChatScope(
        type=ScopeType.VIEWPORT,
        bbox=BoundingBox(north=60.0, south=30.0, east=60.0, west=20.0),
    )
    assert "north=60.0" in scope.describe()
    assert "west=20.0" in scope.describe()


def test_bounding_box_rejects_inverted_latitudes() -> None:
    with pytest.raises(ValidationError, match="north must be greater"):
        BoundingBox(north=10.0, south=20.0, east=30.0, west=-30.0)


@pytest.mark.parametrize(
    ("north", "south"),
    [(91.0, 0.0), (-1.0, -91.0)],
)
def test_bounding_box_rejects_out_of_range_latitudes(
    north: float, south: float
) -> None:
    with pytest.raises(ValidationError, match="latitudes must be within"):
        BoundingBox(north=north, south=south, east=30.0, west=-30.0)


@pytest.mark.parametrize(
    ("east", "west"),
    [(181.0, 0.0), (1.0, -181.0)],
)
def test_bounding_box_rejects_out_of_range_longitudes(east: float, west: float) -> None:
    with pytest.raises(ValidationError, match="longitudes must be within"):
        BoundingBox(north=10.0, south=-10.0, east=east, west=west)


def test_chat_turn_rejects_blank_content() -> None:
    with pytest.raises(ValidationError, match="content must not be blank"):
        ChatTurn(role="user", content="   ")


def test_chat_turn_strips_content() -> None:
    turn = ChatTurn(role="assistant", content="  hello  ")
    assert turn.content == "hello"


def test_chat_turn_rejects_oversized_content() -> None:
    with pytest.raises(ValidationError):
        ChatTurn(role="user", content="x" * 8001)


def test_chat_plan_rejects_blank_and_oversized_query() -> None:
    with pytest.raises(ValidationError, match="query must not be blank"):
        ChatPlan(query="   ")
    with pytest.raises(ValidationError):
        ChatPlan(query="x" * 501)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "x" * 101),
        ("location", "x" * 201),
        ("web_query", "x" * 401),
    ],
)
def test_chat_plan_rejects_oversized_optional_fields(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        ChatPlan(query="query", **{field: value})


def test_chat_plan_drops_blank_optional_fields() -> None:
    plan = ChatPlan(
        query="query",
        category="  ",
        location="",
        web_query="   ",
    )
    assert plan.category is None
    assert plan.location is None
    assert plan.web_query is None


def test_plan_time_range_rejects_reversed_range() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValidationError, match="start must be before"):
        PlanTimeRange(start=start, end=start - timedelta(days=1))


def test_plan_time_range_accepts_equal_bounds() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    assert PlanTimeRange(start=start, end=start).start == start


def test_web_result_caps_title_and_snippet() -> None:
    with pytest.raises(ValidationError):
        WebResult(
            title="x" * 301,
            url="https://example.com",
            retrieved_at=datetime.now(UTC),
        )
    with pytest.raises(ValidationError):
        WebResult(
            title="title",
            url="https://example.com",
            retrieved_at=datetime.now(UTC),
            snippet="x" * 1201,
        )


def test_source_kind_values() -> None:
    assert {kind.value for kind in ChatSourceKind} == {
        "event",
        "article",
        "timeline",
        "web",
    }
