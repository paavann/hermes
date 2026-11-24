from __future__ import annotations

import enum
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from hermes_ai.utils.coercion import coerce_to_str


class LabelArticleType(enum.StrEnum):
    BREAKING = "BREAKING"
    DEVELOPMENT = "DEVELOPMENT"
    ANALYSIS = "ANALYSIS"
    FEATURE = "FEATURE"
    OPINION = "OPINION"
    LISTICLE = "LISTICLE"
    OTHER = "OTHER"


class LabelEventForm(enum.StrEnum):
    INCIDENT = "INCIDENT"
    PLANNED_EVENT = "PLANNED_EVENT"
    POLICY_ACTION = "POLICY_ACTION"
    STATEMENT = "STATEMENT"
    REPORT = "REPORT"
    MARKET_MOVE = "MARKET_MOVE"
    OTHER = "OTHER"


class LabelCertainty(enum.StrEnum):
    CONFIRMED = "CONFIRMED"
    REPORTED = "REPORTED"
    ALLEGED = "ALLEGED"
    DISPUTED = "DISPUTED"


class LabelCategory(enum.StrEnum):
    CONFLICT = "CONFLICT"
    DISASTER = "DISASTER"
    ECONOMY = "ECONOMY"
    POLITICS = "POLITICS"
    TECHNOLOGY = "TECHNOLOGY"
    SCIENCE = "SCIENCE"
    HEALTH = "HEALTH"
    ENVIRONMENT = "ENVIRONMENT"
    SPORTS = "SPORTS"
    ENTERTAINMENT = "ENTERTAINMENT"
    OTHER = "OTHER"


class LabelScope(enum.StrEnum):
    GLOBAL = "GLOBAL"
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    CITY = "CITY"
    LOCAL = "LOCAL"


class LabelEntityKind(enum.StrEnum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    PRODUCT = "PRODUCT"
    OTHER = "OTHER"


class LabelLocation(BaseModel):
    """A location name without coordinates."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="A clean place name such as 'Kyiv, Ukraine' or 'Japan'."
    )
    country_code: str | None = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country code, uppercase, or null.",
    )

    @field_validator("name", mode="before")
    @classmethod
    def coerce_name(cls, value: object) -> str:
        return coerce_to_str(value)

    @field_validator("country_code", mode="before")
    @classmethod
    def coerce_country_code(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = coerce_to_str(value).upper()
        return cleaned if len(cleaned) == 2 and cleaned.isalpha() else None


class LabelEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="The entity's canonical name.")
    kind: LabelEntityKind = Field(description="The entity kind.")

    @field_validator("name", mode="before")
    @classmethod
    def coerce_name(cls, value: object) -> str:
        return coerce_to_str(value)

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: object) -> object:
        return _normalize_enum_value(value, default="OTHER")


class ArticleLabelExtraction(BaseModel):
    """One article label as returned by the labeler."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(
        ge=0,
        description="The 0-based position of the article in the input batch.",
    )
    is_event: bool = Field(
        description="True only for a specific real-world occurrence with a place."
    )
    article_type: LabelArticleType = Field(
        description="The article's genre, not its topic."
    )
    event_form: LabelEventForm | None = Field(
        default=None,
        description="The occurrence type, or null for a non-event.",
    )
    category: LabelCategory = Field(
        description="The closed topic category.",
    )
    specificity: int = Field(
        ge=1,
        le=5,
        description="1 = vague, 5 = exact actor, action, place, and time.",
    )
    consequence: int = Field(
        ge=1,
        le=5,
        description="1 = negligible, 5 = severe or far-reaching.",
    )
    certainty: LabelCertainty | None = Field(
        default=None,
        description="How strongly the central claim is established.",
    )
    fact: str | None = Field(
        default=None,
        max_length=400,
        description="One neutral sentence: who did what, where, and when.",
    )
    event_time: datetime | None = Field(
        default=None,
        description="The occurrence time in ISO 8601 with a timezone.",
    )
    locations: list[LabelLocation] = Field(
        default_factory=list,
        max_length=3,
        description="At most three location names; never coordinates.",
    )
    entities: list[LabelEntity] = Field(
        default_factory=list,
        max_length=8,
        description="The most relevant named entities.",
    )
    scale_facts: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Numbers and units stated in the text, such as deaths or magnitude.",
    )
    severity: int = Field(
        ge=1,
        le=5,
        description="1 = minor, 5 = catastrophic.",
    )
    scope: LabelScope = Field(
        description="The geographic reach of the occurrence.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="The labeler's confidence in this classification.",
    )
    evidence_quote: str | None = Field(
        default=None,
        max_length=400,
        description="A verbatim span from the supplied text supporting the fact.",
    )
    reject_reason: str | None = Field(
        default=None,
        max_length=200,
        description="A short reason when is_event is false.",
    )

    @field_validator("article_type", mode="before")
    @classmethod
    def normalize_article_type(cls, value: object) -> object:
        return _normalize_enum_value(value, default="OTHER")

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> object:
        return _normalize_enum_value(value, default="OTHER")

    @field_validator("event_form", mode="before")
    @classmethod
    def normalize_event_form(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and value.strip().upper() in {"", "NONE", "NULL"}:
            return None
        return _normalize_enum_value(value, default="OTHER")

    @field_validator("certainty", mode="before")
    @classmethod
    def normalize_certainty(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and value.strip().upper() in {"", "NONE", "NULL"}:
            return None
        return _normalize_enum_value(value, default="REPORTED")

    @field_validator("scope", mode="before")
    @classmethod
    def normalize_scope(cls, value: object) -> object:
        return _normalize_enum_value(value, default="GLOBAL")

    @field_validator("fact", "evidence_quote", "reject_reason", mode="before")
    @classmethod
    def coerce_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = coerce_to_str(value)
        return cleaned or None

    @model_validator(mode="after")
    def populate_missing_event_fields(self) -> ArticleLabelExtraction:
        if not self.is_event:
            return self
        if not self.fact and self.evidence_quote:
            cleaned = " ".join(self.evidence_quote.split())
            if cleaned:
                self.fact = cleaned[:400]
        if not self.locations:
            self.locations = [
                LabelLocation(name=entity.name)
                for entity in self.entities
                if entity.kind == LabelEntityKind.LOCATION and entity.name.strip()
            ][:3]
        return self


class ArticleLabelBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    labels: list[ArticleLabelExtraction] = Field(
        description="One label object per input article, in any order.",
    )

    @model_validator(mode="after")
    def reject_duplicate_indexes(self) -> ArticleLabelBatchResponse:
        seen: set[int] = set()
        for label in self.labels:
            if label.index in seen:
                raise ValueError(f"duplicate label index {label.index}.")
            seen.add(label.index)
        return self


class LabelArticleInput(BaseModel):
    """One article supplied to the labeler."""

    index: int = Field(ge=0)
    title: str
    source: str
    published_at: str | None = None
    language: str | None = None
    summary: str | None = None
    body: str | None = None

    @property
    def quote_source(self) -> str:
        return " ".join(
            part for part in (self.title, self.summary, self.body) if part
        )


def _normalize_enum_value(value: object, *, default: str) -> object:
    if isinstance(value, str):
        candidate = value.strip().upper().replace("-", "_").replace(" ", "_")
        return candidate or default
    return value


__all__ = [
    "ArticleLabelBatchResponse",
    "ArticleLabelExtraction",
    "LabelArticleInput",
    "LabelArticleType",
    "LabelCategory",
    "LabelCertainty",
    "LabelEntity",
    "LabelEntityKind",
    "LabelEventForm",
    "LabelLocation",
    "LabelScope",
]
