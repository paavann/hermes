# Hermes API — Architecture & Design Rationale

> [!NOTE]
> This is human-readable design documentation. It is not auto-loaded into agent context during standard sessions. Consult this document when modifying API endpoints, the causality timeline synthesis pipeline, connection lifecycles, or exception handling.

---

## 1. Application Role & Architectural Boundaries

`hermes-api` is the stateless REST API and on-demand historical timeline synthesis engine of Project Hermes. It acts as the read-optimized bridge connecting PostgreSQL/PostGIS persistence to client applications (`apps/hermes`, `@hermes/map`).

### Key Engineering Decisions ("The Why")

- **12-Factor Statelessness & Zero In-Process Schedulers**: `hermes-api` executes zero cron jobs, background workers, or ingestion loops. All RSS feed harvesting, embedding computation, and time decay are isolated to `hermes-worker`. This architecture prevents asyncio event-loop starvation from long-running network or compute tasks and eliminates split-brain / duplicate task execution when scaling API replicas horizontally across container pods or Uvicorn workers.
- **Data Layer Externalization**: All SQLAlchemy ORM models (`Event`, `Article`, `EventTl`, `GeocodeCache`, `Source`), spatial geometry fields, and Alembic migrations reside exclusively in `libs/shared/hermes-db`. `hermes-api` never defines ORM entities; it interacts strictly through async sessions (`get_db`) and service facades (`EventService`, `EventTlService`). This guarantees a unified data contract across the monorepo and prevents schema drift.
- **Strict Dependency Injection**: Routes in `api/v1/` never instantiate database sessions or services directly. They consume them via FastAPI `Depends()` (`get_event_service`, `get_tl_service`). This decouples request routing from persistence logic and simplifies mocking in unit tests (`tests/test_events_api.py`).

---

## 2. Timeline Engine Orchestration Pipeline

The `POST /api/v1/events/tl/{event_id}` endpoint orchestrates a multi-step causality generation pipeline on demand:

1. **Triage**: An LLM filter (`AiService.analyze_tl_context`) determines if the breaking headline warrants historical context (`is_tl_worthy`) and generates an optimal Wikipedia search query, preventing unnecessary API spend and latency on ephemeral news.
2. **Extraction & Index Resolution**: The MediaWiki service queries Wikipedia. If an index page is detected (e.g., annual chronologies), it enumerates and sorts sub-pages chronologically before fetching extracts in batched requests (`explaintext=1`, up to 50 pages per batch).
3. **Graph Extraction**: An LLM extractor (`hermes-ai`) processes the prose to produce a directed acyclic graph of milestone nodes (dates, headlines, summaries) and causal edges (e.g., `"led to"`, `"triggered"`).
4. **Grounded Geocoding Shield**: Extracted historical location names are geocoded via `GeocodingService` (Nominatim backed by PostgreSQL `geocode_cache`). Coordinates are never hallucinated by the LLM.
5. **Terminal Stitching**: The active breaking event's coordinates are queried from PostGIS (`ST_X`/`ST_Y`) and injected as the terminal leaf node (`id="current-event"`) with its category color. A synthetic causal edge (`relationship="led to"`) connects the final historical milestone to this breaking event.
6. **State Machine & Idempotency**: Status transitions (`GENERATING` -> `READY` / `NO_CONTENT` / `FAILED`) are persisted in `event_timelines` (JSONB nodes/edges). Concurrent requests receive the `GENERATING` state immediately, preventing redundant AI generation runs. Clients can bypass cache via `?force_refresh=true`.

---

## 3. CORS Error Handling Caveat

FastAPI exception handlers registered in `core/errors.py` (`AppException`, `RequestValidationError`, `StarletteHTTPException`, universal `Exception`) construct `JSONResponse` objects directly inside Starlette's `ExceptionMiddleware`. Under certain error conditions, this bypasses the outer `CORSMiddleware`, causing web browsers to mask the true API error behind an opaque CORS error.

To prevent this masking, all custom error handlers must explicitly inject origin headers via `_cors_headers(request)`. Any new exception handler added to the registry must preserve this pattern.

---

## 4. Lifespan & Resiliency

- **Async Lifespan**: `lifespan` in `main.py` initializes the connection pool (`init_db`) on startup and disposes it (`close_db`) on shutdown. No connections are created during module import.
- **Graceful Degradation**: If LLM credentials (`LLM_API`, `LLM_MODEL`) are missing at boot, the server logs a warning and remains operational for spatial queries. The timeline endpoint gracefully returns HTTP 503 instead of crashing the process.
