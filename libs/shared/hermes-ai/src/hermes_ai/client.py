from __future__ import annotations

import logging
from types import TracebackType
from typing import TYPE_CHECKING, Self, cast

from hermes_ai.core.config import AiConfig
from hermes_ai.extractors.adjudicate import PairAdjudicator
from hermes_ai.extractors.describe import DescribeExtractor
from hermes_ai.extractors.labels import LabelExtractor
from hermes_ai.extractors.relationship import RelationshipExtractor
from hermes_ai.extractors.thread import ThreadAssigner
from hermes_ai.extractors.tl import TlExtractor
from hermes_ai.services.llm import LlmService


if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver

    from hermes_ai.chat.engine import AnswerModel, ChatEngine
    from hermes_ai.chat.models.retrieval import ChatRetriever


logger = logging.getLogger(__name__)


class HermesAi:
    def __init__(self, config: AiConfig) -> None:
        self.config = config
        self.llm = LlmService(self.config)
        self.labels = LabelExtractor(self.llm)
        self.timelines = TlExtractor(self.llm)
        self.adjudicator = PairAdjudicator(self.llm)
        self.describer = DescribeExtractor(self.llm)
        self.relationships = RelationshipExtractor(self.llm)
        self.threads = ThreadAssigner(self.llm)
        logger.info("hermes ai initialized.")

    def create_chat_engine(
        self,
        retriever: ChatRetriever,
        *,
        checkpointer: BaseCheckpointSaver[str] | None = None,
    ) -> ChatEngine:
        from langchain_litellm import ChatLiteLLMRouter

        from hermes_ai.chat.engine import ChatEngine
        from hermes_ai.chat.planner import ChatPlanner
        from hermes_ai.chat.tools import build_tools
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
        web_search = (
            WebSearchService(self.config) if self.config.tavily_api_key else None
        )
        tools = build_tools(retriever, web_search)
        router_model = ChatLiteLLMRouter(
            router=self.llm.router,
            model="chat",
            streaming=True,
            temperature=0.2,
            max_tokens=self.config.chat_max_output_tokens,
            request_timeout=self.config.chat_request_timeout_seconds,
            stream_options={"include_usage": self.config.chat_stream_include_usage},
            model_kwargs=self.config.chat_model_kwargs,
        )
        answer_model: AnswerModel = router_model
        if tools:
            try:
                answer_model = cast("AnswerModel", router_model.bind_tools(tools))
            except Exception as exc:
                logger.warning(
                    "chat model cannot bind tools; tool use is disabled: %s.", exc
                )
                tools = []
        return ChatEngine(
            self.llm,
            self.config,
            retriever=retriever,
            planner=planner,
            answer_model=answer_model,
            tools=tools,
            web_search=web_search,
            checkpointer=checkpointer,
            first_token_timeout_seconds=self.config.chat_first_token_timeout_seconds,
            total_timeout_seconds=self.config.chat_total_timeout_seconds,
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
