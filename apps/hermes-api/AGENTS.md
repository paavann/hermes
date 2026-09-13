# Hermes API — AI Agent Context

This document provides backend-specific architectural context for the `hermes-api` FastAPI application. It is scoped to this directory and supplements the root `AGENTS.md`.

---

## 1. Application Role

This is the **backend API and data ingestion engine** of Project Hermes. It is a Python application built with FastAPI, using `uv` for dependency management and `@nxlv/python` for Nx integration. Its responsibilities are:

1. **Ingest** raw news concurrently from RSS feeds on dynamic, per-source schedules.
2. **Deduplicate** articles using `pgvector` semantic similarity and Gemini embeddings to avoid redundant LLM processing.
3. **Extract** geospatial data and metadata from article text using Google GenAI (batched).
4. **Geocode** location names to exact coordinates using Nominatim, backed by a persistent PostGIS cache.
5. **Store** structured event data, embeddings, and geometries in a PostGIS-enabled PostgreSQL database.
6. **Serve** processed events to the frontend via a RESTful API and real-time streams.

---

## 2. Data Ingestion Pipeline

**Crucial Note on Flexibility**: This pipeline is the *current* iteration. It is highly prone to change as newer and better approaches are discovered. You must remain flexible and actively seek better performant approaches rather than blindly sticking to this specific pipeline.

### Pipeline Flow

```text
┌─────────────┐   ┌────────────┐   ┌────────────────┐   ┌──────────────┐   ┌─────────────┐   ┌───────────┐
│ APScheduler │──▶│ feedparser │──▶│ Gemini Embeds  │──▶│ pgvector     │──▶│ Gemini LLM  │──▶│ Nominatim │──▶ PostGIS
│ (5m tick)   │   │ (Parallel) │   │ (Vector Array) │   │ (Similarity) │   │ (Batch Ext) │   │ (Geocode) │
└─────────────┘   └────────────┘   └────────────────┘   └──────────────┘   └─────────────┘   └───────────┘
```

### Stage Details

1. **Scheduling (`apscheduler`)**: Runs a high-frequency "tick-and-check" heartbeat (e.g., every 5 minutes). It dynamically queries the database for active sources where `last_fetched_at + fetch_interval_minutes <= NOW`, ensuring each source is polled on its own independent, optimal schedule.
2. **Fetching (`feedparser`)**: Uses `asyncio.gather` and semaphores to concurrently fetch and parse multiple RSS feeds in parallel. Basic URL-based deduplication is performed instantly against the database to drop already-known articles.
3. **Semantic Filtering (`google-genai` + `pgvector`)**: Instead of naive text hashing, incoming articles are batched and sent to Gemini (`text-embedding-004`) to generate 768-dimensional vector embeddings. We then query PostGIS using the `<=>` cosine distance operator to retrieve only active events that are conceptually identical.
4. **AI Batch Extraction (`google-genai`)**:
   - Send the raw article text and the list of semantically similar candidate events to the Gemini LLM in **batches of 10** (`EXTRACTION_BATCH_SIZE`).
   - The prompt instructs the model to either **merge** the article into an existing candidate event or **create a new event**.
   - **Data Extracted**: Headline, summary (translated to English), category, severity, and **location name** (e.g., "Paris, France").
   - **Hallucination Handling**: If the model fails or returns invalid schemas, log the error and continue. Do not crash the batch.
5. **Geocoding (`geopy` + PostGIS Cache)**: 
   - The extracted location string is passed to Nominatim to get exact lat/long coordinates (replacing pure LLM coordinate hallucination). 
   - Because Nominatim strictly rate-limits (1 req/sec), we use an `asyncio.Lock()`.
   - **Caching**: All geocoding results are permanently stored in a `geocode_cache` PostGIS table to avoid re-querying identical location strings, drastically saving time and preventing IP bans.
6. **Storage (`geoalchemy2` + PostGIS)**:
   - Save the structured event, embedding array, and geocoded coordinates to the database.

### Prompt Management
- All GenAI prompts must be **version-controlled** in the codebase (e.g., `src/hermes_api/prompts/`).
- Never hardcode prompts as inline strings in service functions.

---

## 3. Smart Editor Algorithm

The backend implements a sophisticated ranking algorithm so the frontend's initial load surfaces only the most critical events. The algorithm calculates a `trending_score` based on:

- **Source Credibility Weighting**: Events reported by multiple sources gain score. However, not all sources are equal. A `Source` has a `CredibilityTier` (1 through 4) which dictates its weight. For example, a Tier 1 source (e.g., Reuters) adds +3.0 to an event's score, whereas a Tier 4 tabloid adds +0.5.
- **Semantic Consensus**: If 10 different feeds mention the same event (detected via semantic vector proximity and matched by the LLM), the score compounds rapidly based on those credibility tiers.
- **Time Decay**: To prevent old news from dominating the map, a lifecycle cron job runs every 30 minutes and executes a strict **-10% decay** on the `trending_score` of all `ACTIVE` events. Over 24 hours, an old event will organically drop down the rankings unless continuously refreshed by new articles.

The API exposes this ranking (e.g., `ORDER BY trending_score DESC LIMIT 100`) so the frontend can request top-ranked events.

---

## 4. Database Architecture (PostGIS + pgvector)

### Spatial & Vector Indexing
- **pgvector**: The PostgreSQL Docker image is injected with `postgresql-$PG_MAJOR-pgvector` at runtime via `dockerfile_inline`. 
- **Embeddings**: The `events` table contains an `embedding` column of type `Vector(768)` with an **HNSW index** to enable ultra-fast cosine similarity lookups.
- **GIST indexes**: Required on all geometry columns (`location`, `target_location`). Use `ST_Intersects` with bounding box queries for viewport filtering.

### Caching Tables
- **`geocode_cache`**: Explicitly stores historical location strings and their solved coordinates to bypass external API rate limits (Nominatim).

### Time-Series & Historical Data
- The system retains all historical events. Consider time-based table partitioning as data grows.
- A lifecycle cron job periodically marks events as `STALE` and eventually `ARCHIVED` based on `last_updated_at`, naturally filtering them out of the live map queries.

### Multi-Location Events (Arcs)
- Events involving relationships between two locations (e.g., "Country A sanctions Country B") must store both a `source_location` (Point) and a `target_location` (Point).
- The API must return both coordinates so the frontend can render directional arcs.
- Events with only a single location have `target_location` as `NULL`.

### Scale Target
- The database and API must be architected to comfortably handle **10,000+ active events** simultaneously, with fast spatial and temporal queries.

---

## 5. API Design & Security

### Public vs. Protected Routes
- **Public routes** (map data, event queries): Accessible without authentication but **heavily rate-limited** to prevent scraping. Use IP-based and/or token-bucket rate limiting.
- **Admin/protected routes** (trigger ingestion, manage feeds, configuration): Strictly authenticated. No public access under any circumstances.

### Real-Time Delivery
- Implement a **WebSocket or SSE endpoint** that the frontend subscribes to for live event updates.
- When the ingestion pipeline saves a new event to the database, it must notify connected clients immediately (via an internal pub/sub mechanism or database LISTEN/NOTIFY).
- The real-time stream should support viewport filtering so clients only receive events relevant to their current map view.

### Response Format
- All geospatial API responses must return data in **GeoJSON format** (`FeatureCollection` with `Feature` objects) so the frontend can feed it directly into Mapbox sources without transformation.
- Include event metadata (category, severity, summary, sources, timestamps) as GeoJSON feature `properties`.

---

## 6. Project Structure

The backend follows a modular architecture:

```text
src/hermes_api/
├── main.py              # FastAPI app factory — thin, imports routers
├── api/                 # Route handlers (APIRouter modules)
├── core/                # Configuration, settings, shared utilities
├── db/                  # Database engine, session management, models
├── schemas/             # Pydantic models for API payloads & GenAI
├── services/            # Business logic layer (ingestion, extraction, ranking)
└── scheduler/           # APScheduler job definitions
```

- **`main.py`** must remain thin — only app instantiation, middleware, and router mounting.
- **`api/`** contains modular routers split by domain (events, feeds, admin).
- **`services/`** contains all business logic. Route handlers must delegate to services, never contain business logic themselves.
- **`schemas/`** contains all Pydantic models. Raw dictionaries are forbidden for structured data.
