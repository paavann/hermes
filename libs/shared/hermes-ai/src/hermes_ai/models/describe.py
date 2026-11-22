from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field

from hermes_ai.models.labels import LabelLocation, LabelScope


class DescribeImpact(enum.StrEnum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    MINOR = "MINOR"


class DescribeMemberFact(BaseModel):
    """One family's contribution to an event description."""

    model_config = ConfigDict(extra="forbid")

    fact: str = Field(max_length=400)
    source: str = Field(max_length=120)
    published_at: str | None = None
    entities: list[str] = Field(default_factory=list, max_length=8)
    locations: list[str] = Field(default_factory=list, max_length=3)
    scale_facts: dict[str, str | int | float | bool] = Field(default_factory=dict)


class DescribeEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    category: str = Field(max_length=100)
    facts: list[DescribeMemberFact] = Field(min_length=1, max_length=8)


class EventDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    headline: str = Field(max_length=120, min_length=8)
    summary: str = Field(max_length=900, min_length=20)
    impact_level: DescribeImpact
    scope: LabelScope
    locations: list[LabelLocation] = Field(default_factory=list, max_length=3)


class EventDescriptionBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descriptions: list[EventDescription] = Field(default_factory=list)
