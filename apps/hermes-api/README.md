# Hermes REST API (`hermes-api`)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0_Async-D71F00?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?style=flat&logo=postgresql&logoColor=white)](https://postgis.net)
[![Langfuse](https://img.shields.io/badge/Observability-Langfuse-EE5E2A?style=flat&logo=langfuse&logoColor=white)](https://langfuse.com)
[![Hosting: Amazon Lightsail](https://img.shields.io/badge/Deploy-Amazon_Lightsail-FF9900?style=flat&logo=amazonaws&logoColor=white)](https://aws.amazon.com/lightsail/)

`hermes-api` is the REST API, conversational RAG service, and on-demand historical causality synthesis engine for Project Hermes. Built with **FastAPI** and **Python 3.14+**, it acts as the read-optimized backend connecting PostGIS persistence to the React 19 WebGL frontend client (`apps/hermes`, `@hermes/map`, and `@hermes/chat`). In production, it runs as a single-worker container on an **Amazon Lightsail Container Service** (Nano tier).

---

## Architecture & Boundaries

`hermes-api` operates strictly as a **read and synthesis service**:

- **No Background Work**: The API contains zero background schedulers, cron tasks, or ingestion loops. All RSS harvesting, vector embeddings generation, and score decay processes are isolated in [`apps/hermes-worker`](../hermes-worker).
- **Externalized Data Layer**: All SQLAlchemy 2.0 ORM models (`Event`, `Article`, `EventTl`, `Source`, `GeocodeCache`) and Alembic migrations reside in [`libs/shared/hermes-db`](../../libs/shared/hermes-db). The API interacts through async sessions (`get_db`) and service facades (`EventService`, `EventTlService`).
- **Grounded Geocoding**: The API never prompts LLMs for geographic coordinates. Historical and event locations are resolved strictly through [`GeocodingService`](../../libs/shared/hermes-ai/src/hermes_ai/services/geocoding.py) (OpenStreetMap Nominatim with negative caching).
- **CORS Error Handling**: Custom exception handlers in [`core/errors.py`](src/hermes_api/core/errors.py) explicitly inject origin headers (`_cors_headers(request)`) to prevent Starlette's `ExceptionMiddleware` from masking internal errors behind opaque browser CORS failures.
- **Graceful Degradation**: If LLM credentials are unconfigured, the server remains operational for spatial queries and gracefully returns `HTTP 503` from timeline synthesis and chat endpoints instead of crashing.
- **Conversational RAG**: `POST /api/v1/chat` streams grounded answers over Server-Sent Events. Each request carries only its message, map scope, and `thread_id`; retrieval opens a short-lived database session that is closed before generation starts. Conversation memory is checkpointed per `thread_id` by LangGraph and is process-local in the current deployment, so it does not survive a restart.

> [!NOTE]
> For in-depth architectural sequence diagrams, state machine transitions, and design tradeoffs, see [apps/hermes-api/docs/architecture.md](docs/architecture.md).

---

## REST API Reference

All application endpoints are mounted under the configurable `API_BASE_PATH` prefix (default: `/api/v1`).

### Endpoints Overview

| Method | Path | Description | Response Model |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Health check endpoint returning server liveness status. | `{"message": "hermes is running..."}` |
| `GET` | `/api/v1/events/` | Retrieves a ranked list of events ordered by descending `trending_score`. | `list[EventResponse]` |
| `GET` | `/api/v1/events/bbox` | Spatial bounding box query returning events located within the viewport. | `list[MapEventResponse]` |
| `GET` | `/api/v1/events/{event_id}` | Retrieves full event detail, summary, and linked news articles. | `EventDetailResponse` |
| `POST` | `/api/v1/events/tl/{event_id}` | On-demand timeline synthesis generating an antecedent historical DAG. | `TlResponse` |
| `POST` | `/api/v1/chat` | Streams a grounded conversational answer for the current map scope. | `text/event-stream` |

---

### Key Query Specifications

#### 1. Spatial Viewport Bounding Box (`GET /api/v1/events/bbox`)
Queries the PostGIS spatial index (`ST_Within` on `Geometry(POINT, 4326)`) and projects coordinates directly (`ST_X`, `ST_Y`) for high-performance Mapbox GL rendering:

```bash
curl "http://localhost:8000/api/v1/events/bbox?north=45.0&south=30.0&east=35.0&west=10.0"
```

**Query Parameters**:
- `north` (`float`, -90 to 90): Northern latitude boundary.
- `south` (`float`, -90 to 90): Southern latitude boundary.
- `east` (`float`, -180 to 180): Eastern longitude boundary.
- `west` (`float`, -180 to 180): Western longitude boundary.

#### 2. Event List Query (`GET /api/v1/events/`)
Returns active events sorted by trending score:
- `status` (`string`, optional): Filter by `ACTIVE`, `STALE`, or `ARCHIVED` (default: `ACTIVE`).
- `scope` (`string`, optional): Filter by `GLOBAL`, `COUNTRY`, `STATE`, `CITY`, or `LOCAL`.
- `limit` (`integer`, optional): Max events to return (default: `50`, max: `200`).

#### 3. On-Demand Timeline Synthesis (`POST /api/v1/events/tl/{event_id}`)
Synthesizes a causal historical lineage by triaging the headline, querying the MediaWiki REST API, extracting chronological milestones via LiteLLM, geocoding locations, and stitching the breaking event as the terminal leaf node:

```bash
curl -X POST "http://localhost:8000/api/v1/events/tl/3fa85f64-5717-4562-b3fc-2c963f66afa6?force_refresh=false"
```

**Status States (`TlResponse.status`)**:
- `READY`: Synthesis complete; graph contains historical nodes, edges, and terminal event node.
- `GENERATING`: Synthesis currently in progress.
- `NO_CONTENT`: Event triaged as non-historical or no relevant Wikipedia pages found.
- `FAILED`: Upstream extraction or Wikipedia search failed.

#### 4. Conversational Chat (`POST /api/v1/chat`)
Streams a grounded answer about events in the requested map scope. Conversation memory is keyed by `thread_id` in a LangGraph checkpointer. The current deployment runs with process-local memory (`InMemorySaver`); a persistent `BaseCheckpointSaver` can be injected at the composition root later without changing this contract. Send the same `thread_id` on every turn; the client starts a new thread when the user clears the conversation.

```bash
curl -N -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "What changed in the ceasefire talks this week?",
    "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "scope": {
      "type": "viewport",
      "bbox": { "north": 60, "south": 30, "east": 60, "west": 20 }
    }
  }'
```

**Request limits**:
- `message`: 1–4,000 characters, stripped.
- `thread_id`: UUID that identifies the server-side conversation.
- `retry`: when `true`, the server removes the last user turn from the thread before answering again.
- `scope`: discriminated union of `event` (`event_id`), `viewport` (`bbox` with `north`/`south`/`east`/`west`), or `global` (default).

**SSE event order**:

```text
status(accepted) -> status(planning) -> status(retrieving)
  -> [status(searching)] -> status(generating) -> token* -> sources -> done
```

Each `data:` payload includes a `type` field matching the SSE event name. Every `done` event reports provenance counts, coverage, token usage, whether web search was used, and degraded flags. An `error` event is terminal and may replace `done` after the stream opens; its `code` is one of `RETRIEVAL_FAILED`, `MODEL_TIMEOUT`, `STREAM_TIMEOUT`, `MODEL_FAILED`, `INTERNAL_ERROR`, or `CHAT_BUSY`, with a `retryable` hint. While a long stage is pending the server emits `: keepalive` comments at most every 10 seconds.

**Preflight errors** are returned as JSON before the stream opens: `422 VALIDATION_ERROR`, `429 CHAT_RATE_LIMIT_EXCEEDED` or `CHAT_BUDGET_EXHAUSTED` (with `Retry-After` and `X-RateLimit-*` headers), `503 CHAT_BUSY` (concurrency queue timeout), and `503 CHAT_UNAVAILABLE` (chat disabled or model credentials missing).

**Guards** are in-memory and reset on restart, which suits the single-worker Phase 1 deployment:
- Per-client sliding window: `CHAT_RATE_LIMIT_REQUESTS` per `CHAT_RATE_LIMIT_WINDOW_SECONDS`, keyed by a salted SHA-256 hash of the client IP. `X-Forwarded-For` is honored only when `TRUST_PROXY_HEADERS=true`.
- Daily token budget: `CHAT_DAILY_TOKEN_BUDGET` (`0` disables it). Each turn reserves `ceil(prompt_chars / 4) + CHAT_MAX_OUTPUT_TOKENS` and reconciles against reported usage.
- Concurrency: `CHAT_MAX_CONCURRENT` streams with a `CHAT_QUEUE_TIMEOUT_SECONDS` wait for a slot.

Set `CHAT_ENABLED=false` for an immediate functional rollback; the endpoint then returns `503 CHAT_UNAVAILABLE` without affecting the map or timeline endpoints.

---

### Standard Error Envelope

All API errors return a uniform schema matching `ErrorResponseSchema`:

```json
{
  "err_code": "EVENT_NOT_FOUND",
  "err_msg": "event not found.",
  "details": {
    "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }
}
```

Common error codes: `BUSINESS_LOGIC_ERROR` (400), `EVENT_NOT_FOUND` (404), `VALIDATION_ERROR` (422), `CHAT_RATE_LIMIT_EXCEEDED` / `CHAT_BUDGET_EXHAUSTED` (429), `WIKIPEDIA_SEARCH_ERROR` (502), `CHAT_UNAVAILABLE` / `CHAT_BUSY` / `HTTP_ERROR` / missing credentials (503).

---

## Configuration & Environment Variables

Settings are managed via `pydantic-settings` in [`core/config.py`](src/hermes_api/core/config.py), loading hierarchically from `.env` and `.env.local`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `API_PORT` | `8000` | HTTP port for the Uvicorn listener. |
| `API_BASE_PATH` | `/api/v1` | URL route prefix for all API endpoints. |
| `DB_HOST` | `localhost` | PostgreSQL / Neon database host. |
| `DB_PORT` | `5432` | PostgreSQL database port. |
| `DB_USER` | `postgres` | Database username. |
| `DB_PASSWORD` | *Required* | Database password. |
| `DB_NAME` | `hermes` | Database name. |
| `CHECKPOINT_DB_URL` | `""` | Optional psycopg URL for a persistent LangGraph checkpointer. Defaults to the `DB_*` settings with `ssl` mapped to `sslmode`. Without a reachable saver, chat falls back to process-local `InMemorySaver`. |
| `LLM_API` | `""` | Primary LLM API key (e.g. Mistral). |
| `LLM_MODEL` | `""` | Primary LLM identifier (e.g. `mistral/ministral-8b-latest`). |
| `LLM_API_1` | `None` | Fallback LLM API key (e.g. NVIDIA NIM). |
| `LLM_MODEL_1` | `None` | Fallback model identifier (e.g. `nvidia_nim/openai/gpt-oss-20b`). |
| `EMBED_API` | `""` | Embedding model API key. |
| `EMBED_MODEL` | `""` | Embedding model identifier (`nvidia_nim/nvidia/nemotron-3-embed-1b`). |
| `CHAT_ENABLED` | `true` | Kill switch for `POST /api/v1/chat`. When false, the endpoint returns `503 CHAT_UNAVAILABLE`. |
| `CHAT_MODEL` / `CHAT_API` | `""` | Answer model group. Falls back to `LLM_MODEL` / `LLM_API`. |
| `CHAT_MODEL_1` / `CHAT_API_1` | `None` | Optional fallback answer model group. |
| `PLAN_MODEL` / `PLAN_API` | `""` | Planner model group. Falls back to the resolved chat model. |
| `PLAN_MODEL_1` / `PLAN_API_1` | `None` | Optional fallback planner model group. |
| `TAVILY_API_KEY` | `""` | Tavily news search key. When absent, chat runs without external search. |
| `CHAT_RPM_LIMIT` | `60` | Deployment-level requests-per-minute for the chat and plan router groups. |
| `CHAT_RATE_LIMIT_REQUESTS` | `10` | Per-client request limit within the sliding window. |
| `CHAT_RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding window length in seconds. |
| `CHAT_DAILY_TOKEN_BUDGET` | `500000` | Global daily token budget; `0` disables accounting. |
| `CHAT_MAX_CONCURRENT` | `4` | Maximum concurrent chat streams per worker. |
| `CHAT_QUEUE_TIMEOUT_SECONDS` | `5` | How long a request may wait for a stream slot before `CHAT_BUSY`. |
| `TRUST_PROXY_HEADERS` | `false` | Trust `X-Forwarded-For` for client IP resolution. Enable only behind a trusted proxy. |
| `CHAT_RETRIEVAL_TOP_K` | `8` | Maximum locally retrieved evidence items. |
| `CHAT_MIN_LOCAL_RESULTS` | `2` | Local-result threshold below which web search may run. |
| `CHAT_MIN_SEMANTIC_SIMILARITY` | `0.2` | Minimum semantic similarity for the semantic retrieval branch. |
| `CHAT_FRESHNESS_HOURS` | `24` | Age after which coverage is marked recency-stale. |
| `CHAT_MAX_MESSAGE_CHARS` | `4000` | Maximum current-message length. |
| `CHAT_MAX_OUTPUT_TOKENS` | `1200` | Answer completion budget and budget-reservation component. |
| `CHAT_WEB_TIMEOUT_SECONDS` | `8` | Tavily request timeout. |
| `CHAT_STREAM_INCLUDE_USAGE` | `true` | Request token usage in the answer stream. |
| `CORS_ORIGINS` | `["*"]` | Allowed origins for browser CORS headers. |
| `LANGFUSE_PUBLIC_KEY` | `""` | Langfuse project public key. When set with secret key, activates trace observability. |
| `LANGFUSE_SECRET_KEY` | `""` | Langfuse project secret key. Required alongside public key to enable tracing. |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse ingestion base URL (also accepts alias `LANGFUSE_BASE_URL`). |
| `LANGFUSE_MASK_CONTENT` | `true` | Redact prompt/answer/snippet content from traces. Keep true in production. |

---

## Observability & Tracing (Langfuse)

`hermes-api` integrates with [Langfuse](https://langfuse.com) via `libs/shared/hermes-ai` for end-to-end tracing and performance monitoring of LLM operations during timeline synthesis:

- **Opt-in Activation**: Tracing is strictly opt-in. It activates automatically when both `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are provisioned in the runtime environment. If omitted, LLM calls execute normally without tracing overhead.
- **Instrumented Spans**:
  - `tl-analyze`: Generated by `TlExtractor.analyze`, capturing headline triage decisions and derived search queries.
  - `tl-extract`: Generated by `TlExtractor.extract`, recording Wikipedia prose extraction, milestone resolution, and causal relationship synthesis.
- **Content Masking**: When `LANGFUSE_MASK_CONTENT=true` (default), `LlmService` redacts `input`, `output`, `content`, `messages`, `prompt`, `answer`, `snippet`, and `web_query` values with a key-based `mask` function and an export-stage `mask_otel_spans` hook, while preserving model names and timings. Chat prompts and answers inherit the same masking.
- **Metadata Tagging**: All traces originating from the API are tagged with `["hermes-api", ENV]`, allowing seamless filtering between development and production traffic in the Langfuse dashboard.
- **Graceful Shutdown**: On application shutdown (via `LlmService.aclose()`), the Langfuse client flushes all buffered events (`get_client().flush()`), preventing telemetry loss during container recycling.

---

## Development Runbook

All commands are executed from the monorepo root:

```bash
# Start API in development mode with live reload (port 8000)
npx nx serve hermes-api

# Run unit and integration tests (Pytest)
npx nx test hermes-api

# Lint codebase with Ruff
npx nx lint hermes-api

# Format code with Ruff
npx nx run hermes-api:format

# Apply database migrations to head
npx nx run hermes-api:migrate

# Sync Python virtual environment dependencies
npx nx run hermes-api:sync
```
