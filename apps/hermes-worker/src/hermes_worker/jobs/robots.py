from __future__ import annotations
import logging
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser


logger = logging.getLogger(__name__)

RobotsLoader = Callable[[str], Awaitable[str | None]]


class RobotsCache:
    """Per-run robots.txt cache keyed by origin.

    A failed or missing robots file allows the fetch. A disallow rule blocks
    that URL only; other paths on the same host are still evaluated normally.
    """

    def __init__(self, *, user_agent: str) -> None:
        self._user_agent = user_agent
        self._cache: dict[str, RobotFileParser | None] = {}

    async def allowed(self, url: str, load: RobotsLoader) -> bool:
        parts = urlsplit(url)
        if not parts.scheme or not parts.hostname:
            return False
        origin = f"{parts.scheme}://{parts.hostname.lower()}"
        if parts.port is not None:
            origin = f"{origin}:{parts.port}"

        if origin not in self._cache:
            text = await load(origin)
            if text is None:
                self._cache[origin] = None
            else:
                parser = RobotFileParser()
                parser.parse(text.splitlines())
                self._cache[origin] = parser

        parser = self._cache[origin]
        if parser is None:
            return True
        return parser.can_fetch(self._user_agent, url)
