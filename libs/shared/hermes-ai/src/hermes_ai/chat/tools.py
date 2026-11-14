from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from collections.abc import Sequence

from langgraph.types import Command
from langgraph.prebuilt import InjectedState
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool

from hermes_ai.chat.models.scopes import ChatScope
from hermes_ai.chat.models.retrieval import DegradedFlag, RetrievedEvidence, ChatRetriever
from hermes_ai.chat.state import ChatState
from hermes_ai.chat.web import WebSearcher


logger = logging.getLogger(__name__)

TIMEOUT_SECS = 10.0
MAX_TOOL_SUMMARY_ITEMS = 5


def _evidence_message(evidence: Sequence[RetrievedEvidence]) -> str:
    lines = [f"Retrieved {len(evidence)} plotted event(s) for this query:"]
    lines.extend(f"- {item.headline}" for item in evidence[:MAX_TOOL_SUMMARY_ITEMS])
    return "\n".join(lines)


def _retrieval_tool(retriever: ChatRetriever) -> BaseTool:
    @tool(description="Search plotted news events. Use a short, standalone search query.")
    async def retrieve_events(
        query: str,
        state: Annotated[ChatState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        scope = ChatScope.model_validate(state["scope"])
        try:
            async with asyncio.timeout(TIMEOUT_SECS):
                result = await retriever.retrieve(query, scope=scope)
        except Exception as exc:
            logger.error("tool retrieval failed: %s.", exc)
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content="Local event retrieval failed for that query.",
                            tool_call_id=tool_call_id,
                        )
                    ]
                }
            )

        if not result.evidence:
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content="No additional plotted events matched that query.",
                            tool_call_id=tool_call_id,
                        )
                    ]
                }
            )
        return Command(
            update={
                "extra_evidence": [
                    item.model_dump(mode="json") for item in result.evidence
                ],
                "degraded": [flag.value for flag in result.degraded],
                "messages": [
                    ToolMessage(
                        content=_evidence_message(result.evidence),
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    return retrieve_events


def _web_tool(web: WebSearcher) -> BaseTool:
    @tool(description="Search the web for very recent external news that local events miss.")
    async def web_search(
        query: str,
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        outcome = await web.search(query, recency_intent=True)
        if outcome.degraded:
            return Command(
                update={
                    "degraded": [DegradedFlag.WEB_UNAVAILABLE.value],
                    "messages": [
                        ToolMessage(
                            content="External web search is unavailable right now.",
                            tool_call_id=tool_call_id,
                        )
                    ],
                }
            )

        if not outcome.results:
            return Command(
                update={
                    "web_available": True,
                    "messages": [
                        ToolMessage(
                            content="No external results matched that query.",
                            tool_call_id=tool_call_id,
                        )
                    ],
                }
            )

        titles = "\n".join(
            f"- {item.title}" for item in outcome.results[:MAX_TOOL_SUMMARY_ITEMS]
        )
        return Command(
            update={
                "web_available": True,
                "web_results": [
                    item.model_dump(mode="json") for item in outcome.results
                ],
                "messages": [
                    ToolMessage(
                        content=(
                            f"Retrieved {len(outcome.results)} external result(s):\n"
                            f"{titles}"
                        ),
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    return web_search


def build_tools(
    retriever: ChatRetriever, web: WebSearcher | None = None,
) -> list[BaseTool]:
    tools = [_retrieval_tool(retriever)]
    if web is not None:
        tools.append(_web_tool(web))
    return tools


__all__ = ["build_tools"]
