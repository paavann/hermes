from pydantic import BaseModel, Field, field_validator
from hermes_ai.core.constants import PREDEFINED_CATEGORIES
from hermes_ai.utils.coercion import coerce_to_str


class ArticleInput(BaseModel):
    title: str
    content: str


class ExtractedEvent(BaseModel):
    article_index: int = Field(
        description="The 0-based index of the article this result corresponds to."
    )

    has_location: bool = Field(
        description="""
            True if the article describes an event tied to a specific geographic location.
            False for abstract/global topics.
        """
    )

    location_name: str | None = Field(
        default=None,
        description="""
            The most specific place name. Format 'City, Country'. Null if has_location is false.
        """,
    )

    country_code: str | None = Field(
        default=None,
        description="""
            ISO 3166-1 alpha-2 country code. Null if has_location is false.
        """,
    )

    headline: str = Field(
        description="""
            A concise, neutral, factual headline. Max 100 chars.
        """
    )

    summary: str = Field(
        description="""
            A 2-3 sentence summary of the event.
        """
    )

    category: str = Field(
        description=f"""
            The event category.
            Use one of these predefined categories if it fits: {", ".join(PREDEFINED_CATEGORIES)}.
            Otherwise UPPER_SNAKE_CASE.
        """
    )

    category_color: str | None = Field(
        default=None,
        description="""
            Hex color code if using a custom category. Null if predefined.
        """,
    )

    matched_event_id: str | None = Field(
        default=None,
        description="""
            If this article is about the SAME exact event as an existing active event, set to its ID.
        """,
    )

    @field_validator("has_location", mode="before")
    @classmethod
    def coerce_has_location(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes")
        return bool(v)

    @field_validator("location_name", mode="before")
    @classmethod
    def coerce_location_name(cls, v: object) -> str | None:
        if v is None:
            return None
        res = coerce_to_str(v).strip()
        return res if res else None

    @field_validator("headline", "summary", mode="before")
    @classmethod
    def coerce_strings(cls, v: object) -> str:
        return coerce_to_str(v)


class ExtractionResponse(BaseModel):
    events: list[ExtractedEvent] = Field(
        description="One extraction result per input article."
    )
