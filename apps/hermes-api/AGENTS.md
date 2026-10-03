# Hermes API — AI Agent Context

This document provides backend-specific architectural context for the `hermes-api` FastAPI application. It is scoped to this directory and supplements the root `AGENTS.md`.

---

## 1. Application Role

This is the **stateless backend REST API and on-demand timeline synthesis engine** of Project Hermes. It is a Python application built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostGIS**, **pgvector**, and **LiteLLM**, using `uv` for dependency management and `@nxlv/python` for Nx integration. Its responsibilities are:

1. **Serve** processed events and bounding-box queries to the frontend via a high-performance REST API.
2. **Synthesize** on-demand historical causality graphs (`event_timelines`) from Wikipedia extracts to provide deep context.
3. **Execute** zero background schedulers, adhering strictly to 12-factor stateless process architecture (autonomous RSS ingestion and lifecycle transitions are managed by `apps/hermes-worker`).

---

## 2. Historical Timeline Engine (`tl_service.py`)

Synthesizes on-demand geopolitical lineage for major events:

1. **Triage**: An LLM prompt (`TIMELINE_TRIAGE_SYS_PROMPT`) determines if an event warrants historical Wikipedia context and generates an exact MediaWiki search query.
2. **MediaWiki Extraction**: Searches Wikipedia, detects whether a page is a multi-year timeline index via `enumerate_tl_pages()`, and fetches extracts in batches of 50.
3. **Graph Extraction**: Extracts chronological nodes and causal edges (`"led to"`, `"triggered"`) using `TL_SYSTEM_PROMPT`.
4. **Geocoding & Terminal Stitching**: Resolves coordinates for historical nodes and stitches today's active event as the terminal `"current-event"` node.
5. **Storage**: Persists to `event_timelines` as JSONB `nodes` and `edges`.

---

## 3. Smart Editor Algorithm & Ranking

The API serves events ranked by the smart editor algorithm. While ingestion, consensus score accumulation, and decay transitions are executed autonomously by `hermes-worker`, `hermes-api` queries depend on these signals:

- **Source Credibility Weighting**:
  - `TIER_1` (Reuters, BBC, NYT, WSJ, DW): `+3.0` points
  - `TIER_2` (CNN, Al Jazeera, Euronews): `+2.0` points
  - `TIER_3` (Standard publishers): `+1.0` point
  - `TIER_4` (Aggregators / Tabloids): `+0.5` points
- **Semantic Consensus**: Multiple independent outlets reporting the same incident compound the event's `trending_score`.
- **Hourly Time Decay & Lifecycle**: Maintained by `hermes-worker` (using `run_lifecycle_transitions()`):
  $$\text{trending\_score}_{t+1} = \text{trending\_score}_t \times 0.90$$
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
├── core/                # Settings (multi-env cascade), constants, rate limiter, custom exceptions
├── schemas/             # Pydantic v2 DTOs (events.py, errors.py)
├── services/            # Timeline synthesis (tl_service.py), Wikipedia extraction (wikipedia_service.py), AI timeline graph prompts (ai_service.py), and geocoding fallback (geocoding_service.py)
└── utils/               # Database transaction helpers (db.py)

Shared Data Layer:
└── libs/shared/hermes-db/ # Shared models (Event, Article, Source, GeocodeCache, EventTl), Alembic migrations, session management, and DB services
```