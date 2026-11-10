from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from hermes_ai.core.config import AiConfig


if TYPE_CHECKING:
    from langfuse.types import (
        MaskOtelSpansParams,
        MaskOtelSpansResult,
        OtelSpanIdentifier,
        OtelSpanPatch,
    )


logger = logging.getLogger(__name__)

# Attributes whose values are prompts, completions, retrieved documents, tool
# output, or user input. Remove them before the span leaves the process.
_CONTENT_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "ai.completion",
        "ai.prompt",
        "gen_ai.completion",
        "gen_ai.input.messages",
        "gen_ai.output.messages",
        "gen_ai.prompt",
        "gen_ai.system_instructions",
        "input.value",
        "langfuse.observation.input",
        "langfuse.observation.output",
        "langfuse.trace.input",
        "langfuse.trace.output",
        "llm.content.completion.chunk",
        "llm.input_messages",
        "llm.output_messages",
        "llm.prompt_template.template",
        "llm.prompt_template.variables",
        "output.value",
    }
)

# Terminal path segments used by Langfuse, OpenTelemetry GenAI, OpenInference,
# and application metadata for content-bearing values. Matching the final
# segment keeps operational attributes such as ``gen_ai.usage.input_tokens``
# and ``langfuse.observation.completion_start_time`` intact.
_CONTENT_KEYS: frozenset[str] = frozenset(
    {
        "answer",
        "completion",
        "content",
        "input",
        "messages",
        "output",
        "prompt",
        "snippet",
        "web_query",
    }
)


def _is_content_attribute(key: str) -> bool:
    normalized = key.lower()
    if normalized in _CONTENT_ATTRIBUTES:
        return True
    return normalized.rsplit(".", 1)[-1] in _CONTENT_KEYS


def mask_otel_spans(*, params: MaskOtelSpansParams) -> MaskOtelSpansResult | None:
    """Delete content-bearing attributes from an OpenTelemetry export batch."""
    from langfuse.types import MaskOtelSpansResult, OtelSpanPatch

    patches: dict[OtelSpanIdentifier, OtelSpanPatch] = {}
    for identifier, span in params.spans.items():
        content_keys = tuple(
            key for key in span.attributes if _is_content_attribute(key)
        )
        if content_keys:
            patches[identifier] = OtelSpanPatch(delete_attributes=content_keys)

    if not patches:
        return None
    return MaskOtelSpansResult(span_patches=patches)


def configure_langfuse(config: AiConfig) -> None:
    if not config.langfuse_public_key or not config.langfuse_secret_key:
        logger.warning("langfuse credentials are missing; tracing is disabled.")
        return

    # Imported lazily so that merely importing `hermes_ai` does not load the
    # Langfuse SDK (and, transitively, LangChain) in workers that never use chat
    # or tracing.
    from langfuse import Langfuse

    # Use `base_url` (not the deprecated `host`) so the SDK resolves the OTLP
    # ingestion endpoint correctly.
    Langfuse(
        public_key=config.langfuse_public_key,
        secret_key=config.langfuse_secret_key,
        base_url=config.langfuse_host,
        mask_otel_spans=mask_otel_spans if config.langfuse_mask_content else None,
    )
    logger.info(
        "langfuse tracing initialized. content masking=%s.",
        config.langfuse_mask_content,
    )


def flush_langfuse() -> None:
    from langfuse import get_client

    get_client().flush()
    logger.info("langfuse client flushed.")
