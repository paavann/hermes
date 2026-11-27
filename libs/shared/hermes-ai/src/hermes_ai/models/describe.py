from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hermes_ai.models.labels import LabelLocation, LabelScope
from hermes_ai.utils.coercion import (
    coerce_country_code,
    coerce_to_str,
    normalize_enum_token,
)


class DescribeImpact(enum.StrEnum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    MINOR = "MINOR"


class EventActorKind(enum.StrEnum):
    STATE = "STATE"
    ORGANIZATION = "ORGANIZATION"
    PERSON = "PERSON"
    GROUP = "GROUP"


class EventActorRole(enum.StrEnum):
    ACTOR = "ACTOR"
    TARGET = "TARGET"
    PARTICIPANT = "PARTICIPANT"


class EventActor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=120, min_length=1)
    kind: EventActorKind
    role: EventActorRole
    location_name: str | None = Field(default=None, max_length=160)
    country_code: str | None = Field(default=None, max_length=2)

    @field_validator("name", mode="before")
    @classmethod
    def coerce_name(cls, value: object) -> str:
        return coerce_to_str(value)[:120]

    @field_validator("location_name", mode="before")
    @classmethod
    def coerce_location_name(cls, value: object) -> str | None:
        cleaned = coerce_to_str(value)
        return cleaned[:160] if cleaned else None

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, value: object) -> str | None:
        return coerce_country_code(value)

    @field_validator("kind", "role", mode="before")
    @classmethod
    def normalize_enums(cls, value: object) -> object:
        return normalize_enum_token(value)


class DescribeMemberFact(BaseModel):
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
    actors: list[EventActor] = Field(default_factory=list, max_length=6)


class EventDescriptionBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descriptions: list[EventDescription] = Field(default_factory=list)
