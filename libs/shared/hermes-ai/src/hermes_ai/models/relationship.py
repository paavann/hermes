from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hermes_ai.utils.coercion import normalize_enum_token


class RelationshipKind(enum.StrEnum):
    NONE = "NONE"
    SAME_INCIDENT = "SAME_INCIDENT"
    CAUSED = "CAUSED"
    FOLLOW_UP = "FOLLOW_UP"
    REACTION = "REACTION"
    RELATED = "RELATED"


class RelationshipDirection(enum.StrEnum):
    LEFT_TO_RIGHT = "LEFT_TO_RIGHT"
    RIGHT_TO_LEFT = "RIGHT_TO_LEFT"
    BIDIRECTIONAL = "BIDIRECTIONAL"


class RelationshipEventSide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(max_length=500)
    summary: str | None = Field(default=None, max_length=1_500)
    entities: list[str] = Field(default_factory=list, max_length=10)
    actors: list[str] = Field(default_factory=list, max_length=8)
    location: str | None = Field(default=None, max_length=255)
    country_code: str | None = Field(default=None, max_length=2)
    occurred_at: str | None = None
    category: str = Field(max_length=100)


class RelationshipEvalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int = Field(ge=0)
    left: RelationshipEventSide
    right: RelationshipEventSide


class RelationshipDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int = Field(ge=0)
    relationship: RelationshipKind
    direction: RelationshipDirection = RelationshipDirection.LEFT_TO_RIGHT
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(default="", max_length=240)

    @field_validator("relationship", "direction", mode="before")
    @classmethod
    def normalize_enums(cls, value: object) -> object:
        return normalize_enum_token(value)

    @field_validator("rationale", mode="before")
    @classmethod
    def clamp_rationale(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())[:240]
        return value


class RelationshipBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[RelationshipDecision] = Field(default_factory=list)
