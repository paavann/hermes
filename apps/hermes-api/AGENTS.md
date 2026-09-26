# Hermes API — AI Agent Context

This document provides backend-specific architectural context for the `hermes-api` FastAPI application. It is scoped to this directory and supplements the root `AGENTS.md`.

---

## 1. Application Role

This is the **backend API and autonomous data ingestion engine** of Project Hermes. It is a Python application built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostGIS**, **pgvector**, and **LiteLLM**, using `uv` for dependency management and `@nxlv/python` for Nx integration. Its responsibilities are:

1. **Ingest** raw news concurrently from RSS feeds on dynamic, per-source schedules.
2. **Deduplicate** articles using `pgvector` half-precision semantic embeddings (`halfvec(2048)`) to avoid redundant LLM extraction.
3. **Extract** structured geospatial metadata using LiteLLM (Mistral primary with NVIDIA NIM fallback) enforcing strict Pydantic v2 JSON schemas.
4. **Geocode** location names into verified coordinates using OpenStreetMap Nominatim, shielded by an async rate limiter and persistent PostGIS cache.
5. **Score & Decay** events via a Smart Editor algorithm weighting source credibility tiers and hourly 10% time decay.
6. **Synthesize** on-demand historical causality graphs (`event_timelines`) from Wikipedia extracts to provide deep context.
7. **Serve** processed events and bounding-box queries to the frontend via a high-performance REST API.

---

## 2. Data Ingestion & Timeline Pipelines

### Ingestion Pipeline Flow

```text
┌─────────────┐   ┌────────────┐   ┌────────────────┐   ┌──────────────┐   ┌─────────────┐   ┌───────────┐
│ APScheduler │──▶│ feedparser │──▶│ LiteLLM Embed  │──▶│ pgvector     │──▶│ LiteLLM Ext │──▶│ Nominatim │──▶ PostGIS
│ (Heartbeat) │   │ (Parallel) │   │ (nemotron 2048)│   │ (HNSW < 0.25)│   │ (Mistral/NIM│   │ (Geocode) │
└─────────────┘   └────────────┘   └────────────────┘   └──────────────┘   └─────────────┘   └───────────┘
```

### Stage Details

1. **Scheduling (`apscheduler`)**: Runs an interval heartbeat (`INGESTION_HEARTBEAT_MIN`, default 360m). It queries the database for active sources where `last_fetched_at + fetch_interval_minutes <= NOW()`. On application boot, an immediate background task is launched with `force=True` to guarantee initial data population.
2. **Fetching (`feedparser` + `httpx`)**: Uses `asyncio.Semaphore(5)` to concurrently fetch and parse RSS feeds in parallel. Content is sanitized and truncated to 500 words (`MAX_CONTENT_WORDS`). URL deduplication against the `articles` table immediately drops previously ingested stories.
3. **Semantic Filtering (`litellm` + `pgvector`)**: Batched article texts are converted into 2048-dimensional vector embeddings (`nvidia_nim/nvidia/nemotron-3-embed-1b`) guarded by `EMBED_RPM_LIMIT`. PostGIS is queried using cosine distance against active events (`Event.embedding.cosine_distance(emb) < 0.25`, limit 5 per article) to retrieve candidate duplicates.
4. **AI Batch Extraction (`litellm.Router`)**:
   - Sends article inputs and candidate events to the LLM router in **batches of 10** (`ARTICLE_BATCH_SIZE`) guarded by `RPM_LIMIT`.
   - **Primary Model**: `mistral/ministral-8b-latest`.
   - **Fallback Model**: `nvidia_nim/mistralai/mistral-nemotron`.
   - The model determines whether to merge the article into an existing candidate event or create a new event.
   - Extracted attributes: headline, summary, category, category color (from `PREDEFINED_CATEGORIES`), and location name (e.g., `"Geneva, Switzerland"`).
5. **Geocoding Shield (`geocoding_service.py` + PostGIS Cache)**:
   - Extracted location strings are checked against `geocode_cache` by normalized key (`location_name.strip().lower()`).
   - Cache misses call Nominatim under an `asyncio.Lock()` with a mandatory 1.0-second delay to comply with OpenStreetMap rate limits.
   - Results (including negative `NULL` results) are permanently cached to prevent redundant lookups.
6. **Persistence & Consensus Scoring (`event_service.py`)**:
   - **Matched Event**: Adds `Article`, increments `article_count`, adds source credibility weight to `trending_score`, updates `last_updated_at`, and reactivates event if `STALE`.
   - **New Event**: Inserts `Event` with SRID 4326 `POINT` geometry (`location`), initial credibility score, and embedding vector.

---

### Historical Timeline Engine (`tl_service.py`)

Synthesizes on-demand geopolitical lineage for major events:

1. **Triage**: An LLM prompt (`TIMELINE_TRIAGE_SYS_PROMPT`) determines if an event warrants historical Wikipedia context and generates an exact MediaWiki search query.
2. **MediaWiki Extraction**: Searches Wikipedia, detects whether a page is a multi-year timeline index via `enumerate_tl_pages()`, and fetches extracts in batches of 50.
3. **Graph Extraction**: Extracts chronological nodes and causal edges (`"led to"`, `"triggered"`) using `TL_SYSTEM_PROMPT`.
4. **Geocoding & Terminal Stitching**: Resolves coordinates for historical nodes and stitches today's active event as the terminal `"current-event"` node.
5. **Storage**: Persists to `event_timelines` as JSONB `nodes` and `edges`.

---

## 3. Smart Editor Algorithm

The backend implements an algorithmic ranking model that surfaces critical global events while filtering low-signal noise:

- **Source Credibility Weighting**:
  - `TIER_1` (Reuters, BBC, NYT, WSJ, DW): `+3.0` points
  - `TIER_2` (CNN, Al Jazeera, Euronews): `+2.0` points
  - `TIER_3` (Standard publishers): `+1.0` point
  - `TIER_4` (Aggregators / Tabloids): `+0.5` points
- **Semantic Consensus**: Multiple independent outlets reporting the same incident compound the event's `trending_score`.
- **Hourly Time Decay**: Every 60 minutes, `run_event_lifecycle_job()` executes an automated decay statement across all `ACTIVE` events:
  $$\text{trending\_score}_{t+1} = \text{trending\_score}_t \times 0.90$$
- **Lifecycle Transitions**:
  - `ACTIVE` &rarr; `STALE` after 24 hours without new articles.
  - `STALE` &rarr; `ARCHIVED` after 48 hours without new articles.

---

## 4. Database Architecture (PostGIS + pgvector)

### Spatial & Vector Indexing

- **pgvector**: Uses `halfvec(2048)` with an HNSW index to enable ultra-fast cosine similarity lookups:
  ```sql
  CREATE INDEX idx_events_embedding ON events
  USING hnsw (embedding halfvec_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```
- **GIST Spatial Indexes**: Applied to `location` (`Geometry(POINT, 4326)`). Viewport queries use `ST_Within` with bounding box envelopes (`ST_MakeEnvelope`).
- **Composite B-Tree Indexes**: `idx_events_active_score` on `(status, trending_score)` where `status = 'ACTIVE'`.

### Caching & Graph Tables

- **`geocode_cache`**: Permanently stores normalized location names, latitude, longitude, and display names to eliminate Nominatim rate-limit bottlenecks.
- **`event_timelines`**: Stores JSONB graph nodes and edges linked 1-to-1 with parent events.

---

## 5. API Design & Security

### Endpoints (`/api/v1`)

- `GET /events/`: Returns ranked active events (`status`, `scope`, `limit`).
- `GET /events/bbox`: Spatial query for map viewports (`north`, `south`, `east`, `west`).
- `GET /events/{event_id}`: Eager loads full event summary and associated source articles.
- `POST /events/tl/{event_id}`: Generates or retrieves historical causality timeline (`force_refresh`).

### Structured Error Handling

Managed globally via `register_err_handlers()`:

- `AppException` &rarr; Returns `{ err_code, err_msg, details }`
- `RequestValidationError` &rarr; Returns 422 with validation errors
- `StarletteHTTPException` &rarr; Standardized HTTP errors
- Unhandled exceptions &rarr; 500 with structured internal error schema

---

## 6. Project Structure

```text
src/hermes_api/
├── main.py              # FastAPI app factory, lifespan, CORS, error handler registration
├── api/v1/              # APIRouter modules (router.py, events.py, tl.py)
├── core/                # Settings, constants, rate limiter, custom exceptions, sources.json
├── db/                  # Async engine, session, enums, declarative models (Event, Article, Source, GeocodeCache, EventTl)
├── schemas/             # Pydantic v2 DTOs (events.py, errors.py)
├── services/            # Business logic (ingestion, ai, event, geocoding, rss, source, tl, wikipedia)
├── scheduler/           # APScheduler background workers (jobs.py)
└── utils/               # Database transaction helpers (db.py)
```
