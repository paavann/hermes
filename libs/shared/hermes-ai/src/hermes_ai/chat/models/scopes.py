from __future__ import annotations

import enum
import uuid
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ScopeType(enum.StrEnum):
    EVENT = "event"
    VIEWPORT = "viewport"
    GLOBAL = "global"


class ChatRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class BoundingBox(BaseModel):
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


class ChatScope(BaseModel):
    type: ScopeType
    event_id: uuid.UUID | None = None
    bbox: BoundingBox | None = None

    @model_validator(mode="after")
    def _validate_variant(self) -> Self:
        if self.type is ScopeType.EVENT and self.event_id is None:
            raise ValueError("event scope requires event_id.")
        if self.type is ScopeType.VIEWPORT and self.bbox is None:
            raise ValueError("viewport scope requires bbox.")
        return self

    def describe(self) -> str:
        if self.type is ScopeType.EVENT:
            return f"selected event {self.event_id}."
        if self.type is ScopeType.VIEWPORT and self.bbox is not None:
            return (
                "viewport "
                f"north={self.bbox.north}, south={self.bbox.south}, "
                f"east={self.bbox.east}, west={self.bbox.west}."
            )
        return "all eligible plottings."


class ChatTurn(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=8000)

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content must not be blank.")
        return stripped
