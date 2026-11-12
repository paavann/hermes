"""Tests for chat preflight guards, SSE formatting, and cleanup."""

from __future__ import annotations
import asyncio
import json
import uuid
from types import SimpleNamespace
import pytest
from hermes_ai.chat.models import (
    BoundingBox,
    ChatScope,
    ChatSource,
    ChatSourceKind,
    ChatStage,
    ChatTurn,
    ChatUsage,
    Coverage,
    CoverageLevel,
    DegradedFlag,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    Provenance,
    ScopeType,
    SourcesEvent,
    StatusEvent,
    TokenEvent,
)
from hermes_api.core.exceptions import ChatBusy, ChatRateLimitExceeded
from hermes_api.schemas.chat import (
    ChatEventScope,
    ChatRequest,
    ChatViewportScope,
)
from hermes_api.services.chat_guards import ChatGuards
from hermes_api.services.chat_service import (
    KEEPALIVE_COMMENT,
    ChatService,
)


class FakeRequest:
    def __init__(self, *, disconnected: bool = False) -> None:
        self.client = SimpleNamespace(host="203.0.113.7")
        self.headers: dict[str, str] = {}
        self.disconnected = disconnected

    async def is_disconnected(self) -> bool:
        return self.disconnected


class FakeEngine:
    def __init__(
        self,
        events: list[object],
        *,
        delay_seconds: float = 0.0,
    ) -> None:
        self.events = events
        self.delay_seconds = delay_seconds
        self.calls: list[dict[str, object]] = []

    async def stream(
        self,
        message: str,
        *,
        history: tuple[ChatTurn, ...] = (),
        scope: ChatScope,
    ):
        self.calls.append(
            {
                "message": message,
                "history": history,
                "scope": scope,
            }
        )
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        for event in self.events:
            yield event


class FakeRuntime:
    def __init__(self, engine: FakeEngine, guards: ChatGuards) -> None:
        self.engine = engine
        self.guards = guards
        self.max_output_tokens = 1200


def _guards(
    *,
    rate_limit_requests: int = 10,
    daily_token_budget: int = 10_000,
    max_concurrent: int = 2,
    queue_timeout_seconds: float = 0.01,
) -> ChatGuards:
    return ChatGuards(
        rate_limit_requests=rate_limit_requests,
        rate_limit_window_seconds=60.0,
        daily_token_budget=daily_token_budget,
        max_concurrent=max_concurrent,
        queue_timeout_seconds=queue_timeout_seconds,
        trust_proxy_headers=False,
        salt=b"0123456789abcdef0123456789abcdef",
    )


def _service(engine: FakeEngine, guards: ChatGuards) -> ChatService:
    return ChatService(FakeRuntime(engine, guards))


def _source() -> ChatSource:
    return ChatSource(
        kind=ChatSourceKind.EVENT,
        id="E1",
        event_id=uuid.uuid4(),
        title="Flooding in Valencia",
        latitude=39.47,
        longitude=-0.37,
    )


def _done(*, total_tokens: int = 15) -> DoneEvent:
    return DoneEvent(
        provenance=Provenance(events=1),
        coverage=Coverage(level=CoverageLevel.SUFFICIENT, result_count=1),
        usage=ChatUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=total_tokens,
        ),
        web_used=False,
        degraded=(DegradedFlag.PLANNER_FALLBACK,),
    )


def _frames(frame: str) -> tuple[str, dict[str, object]]:
    lines = frame.strip().splitlines()
    event = lines[0].removeprefix("event: ")
    data = json.loads(lines[1].removeprefix("data: "))
    return event, data


def test_prepare_maps_scope_history_and_reserves_capacity() -> None:
    async def run() -> None:
        guards = _guards()
        service = _service(FakeEngine([]), guards)
        event_id = uuid.uuid4()
        payload = ChatRequest(
            message="what happened?",
            history=[
                {"role": "user", "content": "earlier question"},
                {"role": "assistant", "content": "earlier answer [E1]"},
            ],
            scope=ChatEventScope(event_id=event_id),
        )

        turn = await service.prepare(FakeRequest(), payload)

        assert turn.scope.type is ScopeType.EVENT
        assert turn.scope.event_id == event_id
        assert [item.role.value for item in turn.history] == [
            "user",
            "assistant",
        ]
        assert guards.budget.reserved > 0
        assert guards.concurrency.available == 1

        turn.settle(None)
        assert guards.budget.reserved == 0
        assert guards.budget.used == 0
        assert guards.concurrency.available == 2

    asyncio.run(run())


def test_prepare_maps_viewport_bounds() -> None:
    async def run() -> None:
        service = _service(FakeEngine([]), _guards())
        payload = ChatRequest(
            message="flooding",
            scope=ChatViewportScope(
                bbox={"north": 51.0, "south": 40.0, "east": 10.0, "west": -10.0}
            ),
        )

        turn = await service.prepare(FakeRequest(), payload)

        assert turn.scope.type is ScopeType.VIEWPORT
        assert turn.scope.bbox == BoundingBox(
            north=51.0, south=40.0, east=10.0, west=-10.0
        )
        turn.settle(None)

    asyncio.run(run())


def test_stream_emits_ordered_sse_and_reconciles_usage() -> None:
    async def run() -> list[str]:
        guards = _guards()
        engine = FakeEngine(
            [
                StatusEvent(stage=ChatStage.ACCEPTED),
                StatusEvent(stage=ChatStage.GENERATING),
                TokenEvent(text="Hello "),
                TokenEvent(text="[E1]"),
                SourcesEvent(sources=(_source(),)),
                _done(),
            ]
        )
        service = _service(engine, guards)
        turn = await service.prepare(
            FakeRequest(), ChatRequest(message="what happened?")
        )

        frames = [frame async for frame in service.stream(turn, FakeRequest())]

        assert guards.budget.used == 15
        assert guards.budget.reserved == 0
        assert guards.concurrency.available == 2
        return frames

    frames = asyncio.run(run())
    parsed = [_frames(frame) for frame in frames]

    assert [name for name, _ in parsed] == [
        "status",
        "status",
        "token",
        "token",
        "sources",
        "done",
    ]
    assert parsed[0][1] == {"type": "status", "stage": "accepted"}
    assert parsed[2][1] == {"type": "token", "text": "Hello "}
    assert parsed[4][1]["sources"][0]["kind"] == "event"
    assert parsed[5][1]["usage"]["total_tokens"] == 15
    assert parsed[5][1]["degraded"] == ["planner_fallback"]


def test_stream_emits_keepalive_while_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("hermes_api.services.chat_service.KEEPALIVE_SECONDS", 0.01)

    async def run() -> list[str]:
        service = _service(
            FakeEngine(
                [StatusEvent(stage=ChatStage.ACCEPTED)],
                delay_seconds=0.05,
            ),
            _guards(),
        )
        turn = await service.prepare(FakeRequest(), ChatRequest(message="question"))
        return [frame async for frame in service.stream(turn, FakeRequest())]

    frames = asyncio.run(run())

    assert KEEPALIVE_COMMENT in frames
    assert any("accepted" in frame for frame in frames)


def test_closing_the_stream_releases_guards() -> None:
    async def run() -> None:
        guards = _guards()
        service = _service(
            FakeEngine(
                [
                    StatusEvent(stage=ChatStage.ACCEPTED),
                    TokenEvent(text="partial"),
                    _done(),
                ]
            ),
            guards,
        )
        turn = await service.prepare(FakeRequest(), ChatRequest(message="question"))
        stream = service.stream(turn, FakeRequest())

        first = await anext(stream)
        assert "accepted" in first
        await stream.aclose()

        assert guards.budget.used == 0
        assert guards.budget.reserved == 0
        assert guards.concurrency.available == 2

    asyncio.run(run())


def test_error_after_generation_charges_estimate_and_closes() -> None:
    async def run() -> tuple[list[str], ChatGuards]:
        guards = _guards()
        service = _service(
            FakeEngine(
                [
                    StatusEvent(stage=ChatStage.GENERATING),
                    ErrorEvent(
                        code=ErrorCode.MODEL_FAILED,
                        message="The answer model failed.",
                        retryable=True,
                    ),
                ]
            ),
            guards,
        )
        turn = await service.prepare(FakeRequest(), ChatRequest(message="question"))
        estimated = turn.reservation.tokens
        frames = [frame async for frame in service.stream(turn, FakeRequest())]
        assert guards.budget.used == estimated
        return frames, guards

    frames, guards = asyncio.run(run())

    name, data = _frames(frames[-1])
    assert name == "error"
    assert data["code"] == "MODEL_FAILED"
    assert guards.budget.reserved == 0
    assert guards.concurrency.available == 2


def test_missing_terminal_event_emits_internal_error() -> None:
    async def run() -> list[str]:
        service = _service(
            FakeEngine([StatusEvent(stage=ChatStage.ACCEPTED)]),
            _guards(),
        )
        turn = await service.prepare(FakeRequest(), ChatRequest(message="question"))
        return [frame async for frame in service.stream(turn, FakeRequest())]

    frames = asyncio.run(run())

    name, data = _frames(frames[-1])
    assert name == "error"
    assert data["code"] == "INTERNAL_ERROR"
    assert data["retryable"] is True


def test_prepare_enforces_rate_limit_before_reserving() -> None:
    async def run() -> None:
        guards = _guards(rate_limit_requests=1)
        service = _service(FakeEngine([]), guards)
        request = FakeRequest()
        turn = await service.prepare(request, ChatRequest(message="one"))

        with pytest.raises(ChatRateLimitExceeded):
            await service.prepare(request, ChatRequest(message="two"))

        assert guards.budget.reserved > 0
        turn.settle(None)
        assert guards.budget.reserved == 0

    asyncio.run(run())


def test_prepare_releases_budget_when_concurrency_queue_times_out() -> None:
    async def run() -> None:
        guards = _guards(max_concurrent=1, queue_timeout_seconds=0.01)
        service = _service(FakeEngine([]), guards)
        await guards.concurrency.acquire()

        with pytest.raises(ChatBusy):
            await service.prepare(FakeRequest(), ChatRequest(message="question"))

        assert guards.budget.reserved == 0
        assert guards.budget.used == 0
        guards.concurrency.release()
        assert guards.concurrency.available == 1

    asyncio.run(run())


def test_client_disconnect_cancels_stream_and_releases_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "hermes_api.services.chat_service.DISCONNECT_POLL_SECONDS", 0.01
    )

    async def run() -> None:
        guards = _guards()
        engine = FakeEngine(
            [
                StatusEvent(stage=ChatStage.ACCEPTED),
                TokenEvent(text="chunk"),
                _done(),
            ],
            delay_seconds=0.1,
        )
        service = _service(engine, guards)
        turn = await service.prepare(FakeRequest(), ChatRequest(message="question"))
        stream = service.stream(turn, FakeRequest(disconnected=True))
        frames = [frame async for frame in stream]

        assert frames == []
        assert guards.concurrency.available == 2
        assert guards.budget.reserved == 0

    asyncio.run(run())
