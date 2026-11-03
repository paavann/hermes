import logging
from types import TracebackType
from typing import Self

from hermes_ai.core.config import AiConfig
from hermes_ai.extractors.events import EventExtractor
from hermes_ai.extractors.tl import TlExtractor
from hermes_ai.services.llm import LlmService


logger = logging.getLogger(__name__)


class HermesAi:
    def __init__(self, config: AiConfig) -> None:
        self.config = config
        self.llm = LlmService(self.config)
        self.events = EventExtractor(self.llm)
        self.timelines = TlExtractor(self.llm)
        logger.info("hermes ai initialized.")

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
