from pydantic import BaseModel, Field, field_validator
from hermes_ai.utils.coercion import coerce_to_str


class TlNodeExtraction(BaseModel):
    date: str = Field(
        description="""
            the date of the event in YYYY-MM-DD if possible.
        """
    )

    headline: str = Field(
        description="""
            A concise, neutral, factual headline. Max 100 chars.
        """
    )

    location_name: str | None = Field(
        None,
        description="""
            The specific place name (City, Country).
        """,
    )

    summary: str = Field(
        description="""
            A 2-3 sentence summary of the event.
        """
    )

    @field_validator("date", "headline", "summary", mode="before")
    @classmethod
    def coerce_text_fields(cls, v: object) -> str:
        return coerce_to_str(v)

    @field_validator("location_name", mode="before")
    @classmethod
    def coerce_location_name(cls, v: object) -> str | None:
        if v is None:
            return None
        res = coerce_to_str(v).strip()
        return res if res else None


class TlEdgeExtraction(BaseModel):
    source_index: int = Field(
        description="""
            The 0-based index of the cause event in the nodes array.
        """
    )

    target_index: int = Field(
        description="""
            The 0-based index of the effect event in the nodes array.
        """
    )

    relationship: str = Field(
        description="""
            A 1-2 word description of the relationship (e.g., 'triggered', 'retaliated').
        """
    )

    @field_validator("relationship", mode="before")
    @classmethod
    def coerce_relationship(cls, v: object) -> str:
        return coerce_to_str(v)


class TlExtractionResponse(BaseModel):
    tl_summary: str = Field(
        description="""
            A 1-2 paragraph summary of the entire timeline.
        """
    )

    nodes: list[TlNodeExtraction] = Field(
        description="""
            The chronological list of events.
        """
    )

    edges: list[TlEdgeExtraction] = Field(
        default_factory=list,
        description="""
            Causal relationships between the extracted nodes.
        """,
    )

    @field_validator("tl_summary", mode="before")
    @classmethod
    def coerce_tl_summary(cls, v: object) -> str:
        return coerce_to_str(v)


class TlSearchQuery(BaseModel):
    is_tl_worthy: bool = Field(
        description="""
            True if this event is part of a major, long-running geopolitical arc (e.g. wars, major diplomatic relations) that would have dedicated Wikipedia coverage.
            False if it is a localized, minor, or isolated incident.
        """
    )

    wiki_search_query: str | None = Field(
        default=None,
        description="""
            If timeline_worthy is true, provide the most relevant Wikipedia search query to find the overarching historical context.
        """,
    )


class GroundedTlNode(TlNodeExtraction):
    latitude: float | None = Field(
        default=None,
        description="Resolved latitude coordinate from geocoding service.",
    )
    longitude: float | None = Field(
        default=None,
        description="Resolved longitude coordinate from geocoding service.",
    )
