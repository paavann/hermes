import uuid
from datetime import datetime
from typing import Annotated, Literal, Self
from pydantic import BaseModel, Field, field_validator, model_validator


ScopeType = Literal["event", "viewport", "global"]
Stage = Literal[
    "accepted",
    "planning",
    "retrieving",
    "searching",
    "generating",
    "finalizing",
]
CoverageLevel = Literal["empty", "thin", "sufficient"]
DegradedFlag = Literal[
    "planner_fallback",
    "semantic_unavailable",
    "web_unavailable",
    "missing_citations",
]
GroundingFlag = Literal["missing_citations"]
SourceKind = Literal["event", "article", "timeline", "web"]
ErrorCode = Literal[
    "RETRIEVAL_FAILED",
    "MODEL_TIMEOUT",
    "STREAM_TIMEOUT",
    "MODEL_FAILED",
    "INTERNAL_ERROR",
    "CHAT_BUSY",
]


class ChatBoundingBox(BaseModel):
    north: float
    south: float
    east: float
    west: float

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.north < self.south:
            raise ValueError("north must be greater than or equal to south.")
        if not -90.0 <= self.south <= 90.0 or not -90.0 <= self.north <= 90.0:
            raise ValueError("latitudes must be within [-90, 90].")
        if not -180.0 <= self.west <= 180.0 or not -180.0 <= self.east <= 180.0:
            raise ValueError("longitudes must be within [-180, 180].")
        return self


class ChatEventScope(BaseModel):
    type: Literal["event"] = "event"
    event_id: uuid.UUID


class ChatViewportScope(BaseModel):
    type: Literal["viewport"] = "viewport"
    bbox: ChatBoundingBox


class ChatGlobalScope(BaseModel):
    type: Literal["global"] = "global"


ChatScope = ChatEventScope | ChatViewportScope | ChatGlobalScope


class ChatMapContext(BaseModel):
    event_id: uuid.UUID | None = None
    bbox: ChatBoundingBox | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: uuid.UUID
    retry: bool = False
    scope: ChatScope | None = None
    context: ChatMapContext | None = None

    @field_validator("message")
    @classmethod
    def _strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be blank.")
        return stripped


class ChatSource(BaseModel):
    kind: SourceKind
    id: str
    event_id: uuid.UUID | None = None
    title: str
    url: str | None = None
    source_name: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_external: bool = False
    snippet: str | None = None


class ChatProvenance(BaseModel):
    events: int = 0
    articles: int = 0
    timeline_nodes: int = 0
    web: int = 0
    background: bool = False
    grounding: list[GroundingFlag] = Field(default_factory=list)


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCoverage(BaseModel):
    level: CoverageLevel
    result_count: int = 0
    best_semantic_similarity: float | None = None
    best_lexical_rank: int | None = None
    newest_age_hours: float | None = None
    recency_stale: bool = False


class ChatDone(BaseModel):
    provenance: ChatProvenance
    coverage: ChatCoverage
    usage: ChatUsage | None = None
    web_used: bool = False
    degraded: list[DegradedFlag] = Field(default_factory=list)


class ChatError(BaseModel):
    code: ErrorCode
    message: str
    retryable: bool = False


class ChatStatusEvent(BaseModel):
    type: Literal["status"] = "status"
    stage: Stage


class ChatTokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class ChatSourcesEvent(BaseModel):
    type: Literal["sources"] = "sources"
    sources: list[ChatSource] = Field(default_factory=list)


class ChatDoneEvent(ChatDone):
    type: Literal["done"] = "done"


class ChatErrorEvent(ChatError):
    type: Literal["error"] = "error"


ChatStreamEvent = Annotated[
    ChatStatusEvent
    | ChatTokenEvent
    | ChatSourcesEvent
    | ChatDoneEvent
    | ChatErrorEvent,
    Field(discriminator="type"),
]


__all__ = [
    "ChatBoundingBox",
    "ChatCoverage",
    "ChatDone",
    "ChatDoneEvent",
    "ChatError",
    "ChatErrorEvent",
    "ChatEventScope",
    "ChatGlobalScope",
    "ChatMapContext",
    "ChatProvenance",
    "ChatRequest",
    "ChatScope",
    "ChatSource",
    "ChatSourcesEvent",
    "ChatStatusEvent",
    "ChatStreamEvent",
    "ChatTokenEvent",
    "ChatUsage",
    "ChatViewportScope",
]
