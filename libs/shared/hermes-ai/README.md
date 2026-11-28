# Hermes AI (`hermes-ai`)

[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Router-blueviolet?style=flat)](https://github.com/BerriAI/litellm)
[![Langfuse](https://img.shields.io/badge/Observability-Langfuse-EE5E2A?style=flat&logo=langfuse&logoColor=white)](https://langfuse.com)
[![OpenStreetMap](https://img.shields.io/badge/Geocoding-Nominatim-7EBC6F?style=flat&logo=openstreetmap&logoColor=white)](https://nominatim.org)

`hermes-ai` is the shared geospatial and conversational intelligence library for Project Hermes. It encapsulates multi-model LLM orchestration, vector embeddings generation, rate-limited and grounded Nominatim geocoding, a LangGraph chat engine, and end-to-end trace observability via Langfuse.

The library is completely decoupled from database ORM models and persistence layers, exposing clean service interfaces and Pydantic schemas consumed by [`apps/hermes-api`](../../../apps/hermes-api) and [`apps/hermes-worker`](../../../apps/hermes-worker). Chat memory is owned by the consumer: `HermesAi.create_chat_engine()` accepts any LangGraph `BaseCheckpointSaver` and never creates database tables or sessions itself.

---

## Core Capabilities

1. **Multi-Model Routing & Schema Validation Failover**:
   Built on LiteLLM's `Router`, managing primary (`mistral/ministral-8b-latest`) and fallback (`nvidia_nim/openai/gpt-oss-20b`) inference deployments. If model output fails Pydantic schema validation (`ValidationError`), `LlmService` automatically catches the error and retries the prompt against the fallback extractor.
2. **Observability & Tracing via Langfuse**:
   Full trace observability powered by the **Langfuse Python SDK v3** (`langfuse>=3.0.0`). Extractor methods are decorated with `@observe(as_type="span", ...)` to record latencies, tokens, and execution states without collecting sensitive input/output text (`capture_input=False, capture_output=False`).
3. **Grounded Geocoding Shield**:
   Enforces OpenStreetMap's 1 req/s acceptable use policy via an asynchronous token-bucket rate limiter (`NominatimResilienceManager`). Features positive in-memory/database caching, in-flight coroutine deduplication (coalescing), circuit breaking (120s cooldown), and negative caching for unresolvable entities.
4. **Vector Embeddings Generation**:
   Generates 2048-dimensional dense vectors using `nvidia_nim/nvidia/nemotron-3-embed-1b` for approximate nearest-neighbor deduplication in PostGIS before LLM extraction passes.
5. **Conversational RAG Engine**:
   Builds a LangGraph `StateGraph` that plans retrieval, runs hybrid local search plus optional Tavily web search, streams grounded answers, and emits citation markers. `ChatEngine` is transport-agnostic and accepts a `ChatRetriever` implementation plus an optional `BaseCheckpointSaver` supplied by the host application.

---

## Observability & Langfuse Integration

Langfuse tracing provides visibility into model routing, latencies, and token spend across all extraction and chat pipelines:

- **Opt-in Activation**: Initialized when both `langfuse_public_key` and `langfuse_secret_key` are provided in `AiConfig`. If omitted, extraction and geocoding run without telemetry overhead.
- **Instrumented Spans** (all configured with `capture_input=False, capture_output=False`):
  - `article-label` (`LabelExtractor.label_batch`): Batch article classification, fact extraction, entities, and location tagging.
  - `event-adjudicate` (`PairAdjudicator.adjudicate_articles`): Pairwise article-to-event clustering adjudication.
  - `event-merge-adjudicate` (`PairAdjudicator.adjudicate_events`): Pairwise duplicate-event merge adjudication.
  - `event-describe` (`DescribeExtractor.describe`): Event headline, summary, impact/scope, location, and actor extraction.
  - `event-relationship` (`RelationshipExtractor.classify`): Pairwise cross-event relationship classification (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`, `SAME_INCIDENT`, `NONE`).
  - `thread-assign` (`ThreadAssigner.assign`): Story thread assignment or new thread naming.
  - `tl-analyze` (`TlExtractor.analyze`): Headline triage and Wikipedia search query derivation.
  - `tl-extract` (`TlExtractor.extract`): Wikipedia prose extraction, milestone resolution, and causal DAG generation.
- **Content Masking**: When `langfuse_mask_content=True` (default), `LlmService` scrubs `input`, `output`, `content`, `messages`, `prompt`, `answer`, `snippet`, and `web_query` values via Langfuse masking and OpenTelemetry span sanitization.
- **Flush-on-Shutdown Guarantee**: The SDK client is cleanly drained via `LlmService.aclose()` -> `get_client().flush()`, ensuring telemetry batches are delivered before process exit or container teardown.
- **Service Tags**: Consumers specify tags (e.g. `["hermes-api", "production"]` or `["hermes-worker", "development"]`) to segment traces in the Langfuse dashboard.

---

## Configuration (`AiConfig`)

The library is configured via the frozen dataclass `AiConfig`:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `routes` | `dict[str, ModelRoute]` | *Required* | Route definitions mapping logical model groups (e.g. `extractor`, `chat`, `plan`, `embed`, or worker task routes `label`, `adjudicate`, `describe`, `relationship`, `thread`) to a `ModelRoute(primary=..., fallbacks=...)`. Each `ModelTarget` supports `rpm`, `tpm`, `model_kwargs`, and `timeout_seconds`. |
| `num_retries` | `int` | `2` | LiteLLM retries per request before failing over or raising. |
| `cooldown_time` | `int` | `180` | Router cooldown in seconds after a deployment failure. |
| `retry_after` | `bool` | `True` | Honor provider `Retry-After` headers. |
| `rpm_limit` | `int \| None` | `None` | Token-bucket rate limit (requests/min) for LLM completions. |
| `tracing_enabled` | `bool` | `False` | Whether Langfuse trace observability is activated. |
| `tracing_tags` | `list[str]` | `[]` | Metadata tags attached to all traces (e.g. `["hermes-worker", "production"]`). |
| `langfuse_public_key` | `str \| None` | `None` | Langfuse project public key. |
| `langfuse_secret_key` | `str \| None` | `None` | Langfuse project secret key. |
| `langfuse_host` | `str \| None` | `None` | Langfuse ingestion endpoint (default: `https://cloud.langfuse.com`). |
| `langfuse_mask_content` | `bool` | `True` | Redact prompt/answer/snippet content from traces. |
| `chat_stream_include_usage` | `bool` | `True` | Request token usage in streamed chat responses. |
| `chat_max_output_tokens` | `int` | `1200` | Answer completion budget. |
| `chat_first_token_timeout_seconds` | `float` | `30.0` | Timeout waiting for the first token from the answer model. |
| `chat_total_timeout_seconds` | `float` | `120.0` | End-to-end streaming timeout for a single chat turn. |
| `chat_request_timeout_seconds` | `float \| None` | `20.0` | Per-request LLM timeout for chat completions. |
| `chat_model_kwargs` / `plan_model_kwargs` | `dict[str, object]` | `{}` | Extra provider parameters for the answer and planner model groups. |
| `web_timeout_seconds` | `float` | `8.0` | Tavily request timeout. |
| `tavily_api_key` | `str \| None` | `None` | Enables external news search when present. |

---

## Programmatic Usage

All external consumers interact with the high-level `HermesAi` facade, which exposes `llm`, `labels`, `timelines`, `adjudicator`, `describer`, `relationships`, `threads`, and `create_chat_engine()`:

```python
from hermes_ai import AiConfig, HermesAi, ModelRoute, ModelTarget

config = AiConfig(
    routes={
        "extractor": ModelRoute(
            primary=ModelTarget(model="mistral/ministral-8b-latest", api_key="..."),
            fallbacks=(
                ModelTarget(model="nvidia_nim/openai/gpt-oss-20b", api_key="..."),
            ),
        ),
        "embed": ModelRoute(
            primary=ModelTarget(
                model="nvidia_nim/nvidia/nemotron-3-embed-1b",
                api_key="...",
                rpm=120,
            ),
        ),
        "chat": ModelRoute(
            primary=ModelTarget(model="mistral/ministral-8b-latest", api_key="..."),
        ),
        "plan": ModelRoute(
            primary=ModelTarget(model="mistral/ministral-8b-latest", api_key="..."),
        ),
    },
    tracing_enabled=True,
    tracing_tags=["hermes-api", "production"],
    langfuse_public_key="pk-lf-...",
    langfuse_secret_key="sk-lf-...",
)

async with HermesAi(config) as ai:
    # Historical timeline synthesis (tl-analyze and tl-extract spans)
    query = await ai.timelines.analyze("Headline of breaking event")
    if query and query.is_tl_worthy:
        timeline = await ai.timelines.extract("Wikipedia_Article_Title", prose="...")
```

### Chat engine

The host application supplies a `ChatRetriever` and, optionally, a LangGraph checkpointer. `hermes-ai` does not open database sessions or create checkpoint tables.

```python
engine = ai.create_chat_engine(retriever, checkpointer=None)
async for event in engine.stream(
    message, thread_id=thread_id, scope=scope, map_context=map_context
):
    # Forward status/token/sources/done events to the transport layer.
    ...
```

The API wires `DbChatRetriever` to `hermes-db`'s `SearchService` and configures `AsyncPostgresSaver` at startup (with `InMemorySaver` fallback if PostgreSQL setup fails).

---

## Development & Testing

Run tests and linting from the monorepo root:

```bash
# Run test suite with Pytest
npx nx test hermes-ai

# Lint with Ruff
npx nx lint hermes-ai

# Format with Ruff
npx nx run hermes-ai:format
```
