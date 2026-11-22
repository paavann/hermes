from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThreadDecision(enum.StrEnum):
    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    UNSURE = "UNSURE"


class ThreadEventSide(BaseModel):
    """One event considered for membership in a story thread."""

    model_config = ConfigDict(extra="forbid")

    headline: str = Field(max_length=500)
    summary: str | None = Field(default=None, max_length=1_500)
    entities: list[str] = Field(default_factory=list, max_length=8)
    location: str | None = Field(default=None, max_length=255)
    occurred_at: str | None = None
    category: str = Field(max_length=100)


class ThreadSide(BaseModel):
    """The persistent story thread the event may join."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1_500)
    entities: list[str] = Field(default_factory=list, max_length=12)
    last_event_at: str | None = None
    event_count: int = Field(ge=0)


class ThreadAssignmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    event: ThreadEventSide
    thread: ThreadSide


class ThreadAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    decision: ThreadDecision
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("decision", mode="before")
    @classmethod
    def normalize_decision(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper().replace("-", "_").replace(" ", "_")
        return value


class ThreadAssignmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[ThreadAssignment] = Field(default_factory=list)
