from __future__ import annotations

import logging
from types import TracebackType
from typing import TYPE_CHECKING, Self

from hermes_ai.core.config import AiConfig
from hermes_ai.extractors.events import EventExtractor
from hermes_ai.extractors.tl import TlExtractor
from hermes_ai.services.llm import LlmService


if TYPE_CHECKING:
    from hermes_ai.chat.engine import ChatEngine
    from hermes_ai.chat.retriever import ChatRetriever


logger = logging.getLogger(__name__)


class HermesAi:
    def __init__(self, config: AiConfig) -> None:
        self.config = config
        self.llm = LlmService(self.config)
        self.events = EventExtractor(self.llm)
        self.timelines = TlExtractor(self.llm)
        logger.info("hermes ai initialized.")

    def create_chat_engine(self, retriever: ChatRetriever) -> ChatEngine:
        from langchain_litellm import ChatLiteLLMRouter
        from hermes_ai.chat.engine import ChatEngine
        from hermes_ai.chat.planner import ChatPlanner
        from hermes_ai.chat.web import WebSearchService
        from hermes_ai.exceptions import ConfigurationError

        if not self.config.has_chat:
            raise ConfigurationError(
                "conversational chat requires a configured chat model group."
            )
        if not self.config.has_plan:
            raise ConfigurationError(
                "conversational chat requires a configured plan model group."
            )
        planner = ChatPlanner(self.llm, self.config)
        answer_model = ChatLiteLLMRouter(
            router=self.llm.router,
            model="chat",
            streaming=True,
            temperature=0.2,
            max_tokens=self.config.chat_max_output_tokens,
            stream_options={"include_usage": self.config.chat_stream_include_usage},
        )
        web_search = (
            WebSearchService(self.config) if self.config.tavily_api_key else None
        )
        return ChatEngine(
            self.llm,
            self.config,
            retriever=retriever,
            planner=planner,
            answer_model=answer_model,
            web_search=web_search,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self.llm.aclose()
