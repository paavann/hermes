from __future__ import annotations

import operator
from typing import Annotated

from langgraph.graph import MessagesState


class ChatState(MessagesState):
    scope: dict[str, object]
    query: str
    plan: dict[str, object]
    retrieval: dict[str, object]
    web_available: bool
    answer: str
    usage: dict[str, int]
    error: str | None
    started_at: float
    web_results: Annotated[list[dict[str, object]], operator.add]
    extra_evidence: Annotated[list[dict[str, object]], operator.add]
    degraded: Annotated[list[str], operator.add]


__all__ = ["ChatState"]
