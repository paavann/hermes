from datetime import datetime
from typing import Protocol

from hermes_db.enums import (
    ArticleCategory,
    ArticleCertainty,
    ArticleType,
    EventForm,
    EventScope,
)


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

    @property
    def category(self) -> ArticleCategory | None: ...

    @property
    def event_form(self) -> EventForm | None: ...

    @property
    def specificity(self) -> int | None: ...

    @property
    def consequence(self) -> int | None: ...

    @property
    def certainty(self) -> ArticleCertainty | None: ...

    @property
    def reject_reason(self) -> str | None: ...

    @property
    def input_hash(self) -> str | None: ...

    @property
    def evidence_quote(self) -> str | None: ...
