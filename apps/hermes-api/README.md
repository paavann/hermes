# Hermes REST API (`hermes-api`)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0_Async-D71F00?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?style=flat&logo=postgresql&logoColor=white)](https://postgis.net)
[![Hosting: Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat&logo=render&logoColor=black)](https://render.com)

`hermes-api` is the stateless REST API and on-demand historical causality synthesis engine for Project Hermes. Built with **FastAPI** and **Python 3.14+**, it acts as the read-optimized backend connecting PostGIS persistence to the React 19 WebGL frontend client (`apps/hermes` and `@hermes/map`). In production, it is deployed as a container service on the Render free-tier plan.

---

## Architecture & Boundaries

`hermes-api` operates strictly as a **read and synthesis service**:

- **12-Factor Statelessness**: The API contains zero background schedulers, cron tasks, or ingestion loops. All RSS harvesting, vector embeddings generation, and score decay processes are isolated in [`apps/hermes-worker`](file:///home/pavan/proj/hermes/apps/hermes-worker).
- **Externalized Data Layer**: All SQLAlchemy 2.0 ORM models (`Event`, `Article`, `EventTl`, `Source`, `GeocodeCache`) and Alembic migrations reside in [`libs/shared/hermes-db`](file:///home/pavan/proj/hermes/libs/shared/hermes-db). The API interacts through async sessions (`get_db`) and service facades (`EventService`, `EventTlService`).
- **Grounded Geocoding**: The API never prompts LLMs for geographic coordinates. Historical and event locations are resolved strictly through [`GeocodingService`](file:///home/pavan/proj/hermes/libs/shared/hermes-ai/src/hermes_ai/services/geocoding.py) (OpenStreetMap Nominatim with negative caching).
- **CORS Error Handling**: Custom exception handlers in [`core/errors.py`](file:///home/pavan/proj/hermes/apps/hermes-api/src/hermes_api/core/errors.py) explicitly inject origin headers (`_cors_headers(request)`) to prevent Starlette's `ExceptionMiddleware` from masking internal errors behind opaque browser CORS failures.
- **Graceful Degradation**: If LLM credentials are unconfigured, the server remains operational for spatial queries and gracefully returns `HTTP 503` from timeline synthesis endpoints instead of crashing.

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

Common error codes: `BUSINESS_LOGIC_ERROR` (400), `EVENT_NOT_FOUND` (404), `VALIDATION_ERROR` (422), `WIKIPEDIA_SEARCH_ERROR` (502), `HTTP_ERROR` / missing credentials (503).

---

## Configuration & Environment Variables

Settings are managed via `pydantic-settings` in [`core/config.py`](file:///home/pavan/proj/hermes/apps/hermes-api/src/hermes_api/core/config.py), loading hierarchically from `.env` and `.env.local`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `API_PORT` | `8000` | HTTP port for the Uvicorn listener. |
| `API_BASE_PATH` | `/api/v1` | URL route prefix for all API endpoints. |
| `DB_HOST` | `localhost` | PostgreSQL / Neon database host. |
| `DB_PORT` | `5432` | PostgreSQL database port. |
| `DB_USER` | `postgres` | Database username. |
| `DB_PASSWORD` | *Required* | Database password. |
| `DB_NAME` | `hermes` | Database name. |
| `LLM_API` | `""` | Primary LLM API key (e.g. Mistral). |
| `LLM_MODEL` | `""` | Primary LLM identifier (e.g. `mistral/ministral-8b-latest`). |
| `LLM_API_1` | `None` | Fallback LLM API key (e.g. NVIDIA NIM). |
| `LLM_MODEL_1` | `None` | Fallback model identifier (e.g. `nvidia_nim/openai/gpt-oss-20b`). |
| `EMBED_API` | `""` | Embedding model API key. |
| `EMBED_MODEL` | `""` | Embedding model identifier (`nvidia_nim/nvidia/nemotron-3-embed-1b`). |
| `CORS_ORIGINS` | `["*"]` | Allowed origins for browser CORS headers. |

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
