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

Langfuse tracing provides visibility into model routing, latencies, and token spend across all extraction pipelines:

- **Opt-in Activation**: Initialized when both `langfuse_public_key` and `langfuse_secret_key` are provided in `AiConfig`. If omitted, extraction and geocoding run without telemetry overhead.
- **Instrumented Spans**:
  - `event-extract` (`EventExtractor.extract`): Traces batch article deduplication and event consensus evaluation.
  - `tl-analyze` (`TlExtractor.analyze`): Records headline triage and Wikipedia search query derivation.
  - `tl-extract` (`TlExtractor.extract`): Captures Wikipedia prose extraction, milestone resolution, and causal DAG generation.
- **Flush-on-Shutdown Guarantee**: The SDK client is cleanly drained via `LlmService.aclose()` -> `get_client().flush()`, ensuring telemetry batches are delivered before process exit or container teardown.
- **Service Tags**: Consumers specify tags (e.g. `["hermes-api", "production"]` or `["hermes-worker", "development"]`) to segment traces in the Langfuse dashboard.

---

## Configuration (`AiConfig`)

The library is configured via the frozen dataclass `AiConfig`:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `routes` | `dict[str, ModelRoute]` | *Required* | Route definitions mapping logical model groups (`extractor`, `chat`, `plan`, `embed`) to a `ModelRoute(primary=..., fallbacks=...)`. |
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
| `chat_model_kwargs` / `plan_model_kwargs` | `dict[str, object]` | `{}` | Extra provider parameters for the answer and planner model groups. |
| `web_timeout_seconds` | `float` | `8.0` | Tavily request timeout. |
| `tavily_api_key` | `str \| None` | `None` | Enables external news search when present. |

---

## Programmatic Usage

All external consumers interact with the high-level `HermesAi` facade:

```python
from hermes_ai import AiConfig, ArticleInput, HermesAi, ModelRoute, ModelTarget

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
    # 1. Event extraction with Langfuse tracing (event-extract span)
    articles = [ArticleInput(title="...", content="...")]
    events = await ai.events.extract(articles)

    # 2. Historical timeline synthesis (tl-analyze and tl-extract spans)
    query = await ai.timelines.analyze("Headline of breaking event")
    if query and query.is_tl_worthy:
        timeline = await ai.timelines.extract("Wikipedia_Article_Title", prose="...")
```

### Chat engine

The host application supplies a `ChatRetriever` and, optionally, a LangGraph checkpointer. `hermes-ai` does not open database sessions or create checkpoint tables.

```python
engine = ai.create_chat_engine(retriever, checkpointer=None)
async for event in engine.stream(message, thread_id=thread_id, scope=scope):
    # Forward status/token/sources/done events to the transport layer.
    ...
```

The API wires `DbChatRetriever` to `hermes-db`'s `SearchService` and currently passes a process-local `InMemorySaver`; a persistent saver can be supplied without changing the chat contract.

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
