from __future__ import annotations

from typing import Protocol

from hermes_ai.chat.models import ChatScope, RetrievalFilters, RetrievalResult


class ChatRetriever(Protocol):
    async def retrieve(
        self,
        query: str,
        *,
        scope: ChatScope,
        filters: RetrievalFilters | None = None,
        recency_intent: bool = False,
    ) -> RetrievalResult: ...


__all__ = ["ChatRetriever"]
