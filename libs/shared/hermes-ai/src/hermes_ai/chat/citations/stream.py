"""Streaming citation validation and marker sanitization."""

from __future__ import annotations

import re

from hermes_ai.chat.citations.registry import CitationRegistry
from hermes_ai.chat.citations.types import CitationValidation


MARKER_TOKEN_RE = re.compile(r"(?:BG|[EATW]\d+)", re.IGNORECASE | re.ASCII)
# Buffer long enough for split multi-token groups like "[E1, A2, T12, W3]"
# without stalling unclosed prose brackets indefinitely.
MAX_MARKER_HOLD_CHARS = 17


class CitationStreamFilter:
    """Removes invalid markers while holding split markers across chunks."""

    def __init__(self, registry: CitationRegistry) -> None:
        self._registry = registry
        self._buffer = ""
        self._cited: list[str] = []
        self._seen: set[str] = set()
        self._removed = 0

    @property
    def cited_markers(self) -> tuple[str, ...]:
        """Unique valid evidence markers seen so far in first-citation order."""
        return tuple(self._cited)

    @property
    def removed_count(self) -> int:
        """Number of unknown citation tokens stripped from the stream."""
        return self._removed

    def feed(self, text: str) -> str:
        """Process one streamed chunk and emit validated text."""
        self._buffer += text
        output: list[str] = []
        while self._buffer:
            start = self._buffer.find("[")
            if start == -1:
                output.append(self._buffer)
                self._buffer = ""
                break
            output.append(self._buffer[:start])
            remainder = self._buffer[start:]
            end = remainder.find("]")
            if end == -1:
                if len(remainder) <= MAX_MARKER_HOLD_CHARS:
                    self._buffer = remainder
                    break
                # Release only "[" so a subsequent "[" inside remainder can still hold.
                output.append("[")
                self._buffer = remainder[1:]
                continue
            candidate = remainder[: end + 1]
            output.append(self._render_candidate(candidate))
            self._buffer = remainder[end + 1 :]
        return "".join(output)

    def flush(self) -> str:
        """Drain remaining buffered text and drop any truncated trailing marker."""
        remainder, self._buffer = self._buffer, ""
        if not remainder:
            return ""
        if "[" in remainder and "]" not in remainder:
            remainder = remainder.split("[", 1)[0]
        return remainder

    def _render_candidate(self, candidate: str) -> str:
        content = candidate[1:-1]
        tokens = [token.strip() for token in content.split(",")]
        if not tokens or not any(MARKER_TOKEN_RE.fullmatch(token) for token in tokens):
            return candidate

        rendered: list[str] = []
        for token in tokens:
            normalized = token.upper()
            if normalized == "BG":
                rendered.append("[BG]")
                continue
            if self._registry.resolve(normalized) is None:
                self._removed += 1
                continue
            if normalized not in self._seen:
                self._seen.add(normalized)
                self._cited.append(normalized)
            rendered.append(f"[{normalized}]")
        return "".join(rendered)


def finalize_answer(text: str, registry: CitationRegistry) -> CitationValidation:
    """Validate a complete answer string and summarize citation coverage."""
    stream = CitationStreamFilter(registry)
    cleaned = stream.feed(text) + stream.flush()
    return CitationValidation(
        cleaned_text=cleaned,
        cited_markers=stream.cited_markers,
        removed_count=stream.removed_count,
        has_background="[BG]" in cleaned,
        has_citation=bool(stream.cited_markers),
    )


__all__ = [
    "CitationStreamFilter",
    "MARKER_TOKEN_RE",
    "MAX_MARKER_HOLD_CHARS",
    "finalize_answer",
]
