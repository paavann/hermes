from datetime import datetime
from typing import Protocol

from hermes_db.enums import ArticleType, EventScope


class EventExtractionData(Protocol):
    """Structural contract for AI-extracted event metadata passed into persistence."""

    @property
    def headline(self) -> str: ...

    @property
    def summary(self) -> str: ...

    @property
    def category(self) -> str: ...

    @property
    def category_color(self) -> str | None: ...

    @property
    def location_name(self) -> str | None: ...

    @property
    def country_code(self) -> str | None: ...

    @property
    def impact_level(self) -> str | None: ...


class EventSynthesisData(Protocol):
    """Structural contract for the described output of one event cluster."""

    @property
    def headline(self) -> str: ...

    @property
    def summary(self) -> str: ...

    @property
    def category(self) -> str: ...

    @property
    def category_color(self) -> str | None: ...

    @property
    def location_name(self) -> str | None: ...

    @property
    def country_code(self) -> str | None: ...

    @property
    def impact_level(self) -> str | None: ...

    @property
    def event_time(self) -> datetime | None: ...

    @property
    def confidence(self) -> float | None: ...


class ArticleLabelData(Protocol):
    """Structural contract for the cheap per-article classification output."""

    @property
    def is_event(self) -> bool: ...

    @property
    def article_type(self) -> ArticleType: ...

    @property
    def event_time(self) -> datetime | None: ...

    @property
    def severity(self) -> int | None: ...

    @property
    def scope(self) -> EventScope | None: ...

    @property
    def confidence(self) -> float | None: ...

    @property
    def fact(self) -> str | None: ...

    @property
    def scale_facts(self) -> dict[str, object]: ...

    @property
    def entities(self) -> list[dict[str, object]]: ...

    @property
    def locations(self) -> list[dict[str, object]]: ...


class GeocodingData(Protocol):
    """Structural contract for resolved geographic coordinates."""

    @property
    def latitude(self) -> float: ...

    @property
    def longitude(self) -> float: ...
