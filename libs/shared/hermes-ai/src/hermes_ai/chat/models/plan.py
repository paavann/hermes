from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from hermes_ai.chat.models.scopes import ChatMapContext, ChatScope, ChatTurn, ScopeType


@dataclass(frozen=True, slots=True)
class PlannerOutcome:
    plan: ChatPlan
    degraded: bool = False
    failure: str | None = None


class Planner(Protocol):
    async def plan(
        self,
        message: str,
        *,
        history: Sequence[ChatTurn] = (),
        scope: ChatScope,
        map_context: ChatMapContext | None = None,
    ) -> PlannerOutcome: ...


class PlanTimeRange(BaseModel):
    start: datetime | None = None
    end: datetime | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> Self:
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be before or equal to end.")
        return self


class ChatPlan(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    time_range: PlanTimeRange | None = None
    needs_web: bool = False
    web_query: str | None = Field(default=None, max_length=400)
    recency_intent: bool = False
    target_scope: ScopeType | None = None
    browse: bool = False

    @field_validator("query")
    @classmethod
    def _strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be blank.")
        return stripped

    @field_validator("category", "location", "web_query")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
