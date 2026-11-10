from __future__ import annotations

import enum
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from pydantic import BaseModel, Field

from hermes_ai.chat.models.retrieval import Coverage, DegradedFlag
from hermes_ai.chat.models.sources import ChatSource, GroundingFlag


class ChatStage(enum.StrEnum):
    ACCEPTED = "accepted"
    PLANNING = "planning"
    RETRIEVING = "retrieving"
    SEARCHING = "searching"
    GENERATING = "generating"
    FINALIZING = "finalizing"


class ErrorCode(enum.StrEnum):
    RETRIEVAL_FAILED = "RETRIEVAL_FAILED"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    STREAM_TIMEOUT = "STREAM_TIMEOUT"
    MODEL_FAILED = "MODEL_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Provenance(BaseModel):
    events: int = 0
    articles: int = 0
    timeline_nodes: int = 0
    web: int = 0
    background: bool = False
    grounding: list[GroundingFlag] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class StatusEvent:
    stage: ChatStage


@dataclass(frozen=True, slots=True)
class TokenEvent:
    text: str


@dataclass(frozen=True, slots=True)
class SourcesEvent:
    sources: tuple[ChatSource, ...] = ()


@dataclass(frozen=True, slots=True)
class DoneEvent:
    provenance: Provenance
    coverage: Coverage
    usage: ChatUsage | None = None
    web_used: bool = False
    degraded: tuple[DegradedFlag, ...] = dataclass_field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    code: ErrorCode
    message: str
    retryable: bool = False


EngineEvent = StatusEvent | TokenEvent | SourcesEvent | DoneEvent | ErrorEvent
