from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hermes_ai.utils.coercion import normalize_enum_token


class PairDecision(enum.StrEnum):
    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    UNSURE = "UNSURE"


class PairSide(BaseModel):
    """One side of a candidate event/article comparison."""

    model_config = ConfigDict(extra="forbid")

    headline: str = Field(max_length=500)
    fact: str | None = Field(default=None, max_length=400)
    summary: str | None = Field(default=None, max_length=1_500)
    entities: list[str] = Field(default_factory=list, max_length=8)
    actors: list[str] = Field(default_factory=list, max_length=8)
    location: str | None = Field(default=None, max_length=255)
    occurred_at: str | None = None
    category: str = Field(max_length=100)


class PairAdjudicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    left: PairSide
    right: PairSide


class PairAdjudication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    decision: PairDecision
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("decision", mode="before")
    @classmethod
    def normalize_decision(cls, value: object) -> object:
        return normalize_enum_token(value)


class PairAdjudicationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[PairAdjudication] = Field(default_factory=list)
