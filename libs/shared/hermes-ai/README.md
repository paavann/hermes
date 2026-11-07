# Hermes AI (`hermes-ai`)

[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Router-blueviolet?style=flat)](https://github.com/BerriAI/litellm)
[![Langfuse](https://img.shields.io/badge/Observability-Langfuse-EE5E2A?style=flat&logo=langfuse&logoColor=white)](https://langfuse.com)
[![OpenStreetMap](https://img.shields.io/badge/Geocoding-Nominatim-7EBC6F?style=flat&logo=openstreetmap&logoColor=white)](https://nominatim.org)

`hermes-ai` is the shared geospatial intelligence library for Project Hermes. It encapsulates multi-model LLM orchestration, vector embeddings generation, rate-limited and grounded Nominatim geocoding, and end-to-end trace observability via Langfuse.

The library is completely decoupled from database ORM models and persistence layers, exposing clean service interfaces and Pydantic schemas consumed by [`apps/hermes-api`](../../apps/hermes-api) and [`apps/hermes-worker`](../../apps/hermes-worker).

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
| `primary_model` | `str` | *Required* | LiteLLM model identifier for primary extraction. |
| `primary_api_key` | `str` | *Required* | API key for primary model provider. |
| `fallback_model` | `str \| None` | `None` | Secondary fallback model identifier. |
| `fallback_api_key` | `str \| None` | `None` | API key for fallback model provider. |
| `embed_model` | `str \| None` | `None` | Dense embedding model identifier. |
| `embed_api_key` | `str \| None` | `None` | Embedding model API key. |
| `rpm_limit` | `int \| None` | `None` | Token-bucket rate limit (requests/min) for LLM completions. |
| `embed_rpm_limit` | `int \| None` | `None` | Rate limit (requests/min) for embedding generation. |
| `tracing_enabled` | `bool` | `False` | Whether Langfuse trace observability is activated. |
| `tracing_tags` | `list[str]` | `[]` | Metadata tags attached to all traces (e.g. `["hermes-worker", "production"]`). |
| `langfuse_public_key` | `str \| None` | `None` | Langfuse project public key. |
| `langfuse_secret_key` | `str \| None` | `None` | Langfuse project secret key. |
| `langfuse_host` | `str \| None` | `None` | Langfuse ingestion endpoint (default: `https://cloud.langfuse.com`). |

---

## Programmatic Usage

All external consumers interact with the high-level `HermesAi` facade:

```python
from hermes_ai import AiConfig, ArticleInput, HermesAi

config = AiConfig(
    primary_model="mistral/ministral-8b-latest",
    primary_api_key="...",
    fallback_model="nvidia_nim/openai/gpt-oss-20b",
    fallback_api_key="...",
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
