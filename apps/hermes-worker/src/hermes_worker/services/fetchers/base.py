from datetime import datetime
from typing import Protocol
from hermes_db.services.source import DueSource
from pydantic import BaseModel, computed_field


MAX_WORDS: int = 500


def _truncate_to_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    else:
        return " ".join(words[:max_words]) + "..."


class ParsedArticle(BaseModel):
    title: str
    url: str
    description: str
    content: str | None = None
    published_at: datetime | None = None
    source_country: str | None = None

    @computed_field
    @property
    def text_for_ai(self) -> str:
        if self.content:
            return _truncate_to_words(self.content, MAX_WORDS)
        return self.description


class BaseArticleFetcher(Protocol):
    async def fetch_articles(self, source: DueSource) -> list[ParsedArticle]: ...
