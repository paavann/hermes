# Hermes API — AI Agent Context

This document provides backend-specific architectural context for the `hermes-api` FastAPI application. It is scoped to this directory and supplements the root `AGENTS.md`.

---

## 1. Application Role

This is the **backend API and data ingestion engine** of Project Hermes. It is a Python application built with FastAPI, using `uv` for dependency management and `@nxlv/python` for Nx integration. Its responsibilities are:

1. **Ingest** raw news from RSS feeds on a schedule.
2. **Deduplicate** articles to avoid redundant AI processing.
3. **Extract** geospatial data from article text using Google GenAI.
4. **Store** structured event data in a PostGIS-enabled PostgreSQL database.
5. **Serve** processed events to the frontend via a RESTful API and real-time stream.

---

## 2. Data Ingestion Pipeline

**Crucial Note on Flexibility**: This pipeline is the *current* iteration. It is highly prone to change as newer and better approaches are discovered. You must remain flexible and actively seek better performant approaches rather than blindly sticking to this specific pipeline.

### Pipeline Flow

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌─────────┐
│ APScheduler  │────▶│ feedparser  │────▶│ Deduplication    │────▶│ Google GenAI │────▶│ PostGIS │
│ (cron jobs)  │     │ (RSS fetch) │     │ (URL/hash check) │     │ (extraction) │     │ (save)  │
└─────────────┘     └─────────────┘     └──────────────────┘     └──────────────┘     └─────────┘
```

### Stage Details

1. **Scheduling (`apscheduler`)**: Background jobs run on a configurable interval to fetch new articles from a list of RSS feed URLs. The feed list should be configurable (database or config file), not hardcoded.

2. **Fetching (`feedparser`)**: Each RSS feed is parsed to extract individual articles. Extract the title, summary/description, publication date, source URL, and the full article link.

3. **Deduplication (Critical for Cost Control)**:
   - Before sending any article to GenAI, check the database for an existing record with the same URL or a content hash.
   - This is **non-negotiable** — GenAI API calls are expensive, and processing the same article twice is pure waste.
   - Use a combination of the article URL (primary) and a hash of the title + summary (secondary) for robust deduplication.
   - Articles that have already been processed must be skipped silently (no error, just a debug log).

4. **AI Extraction (`google-genai`)**:
   - Send the article text to Google GenAI with a carefully crafted prompt that instructs the model to extract:
     - **Event summary** (translated to English if the source is in another language)
     - **Event category** (e.g., conflict, economic, diplomatic, environmental, humanitarian)
     - **Severity level** (critical, high, moderate, low, positive)
     - **Primary coordinates** (latitude, longitude) — the exact location where the event is happening
     - **Secondary/target coordinates** (optional) — for events involving relationships between two locations (e.g., sanctions between countries)
     - **Affected region** (optional) — polygon/boundary data for territorial events
     - **Source entities** (countries, organizations involved)
   - **Structured Output**: Always use Pydantic models as the expected response schema. Never accept raw unstructured text from the LLM.
   - **Hallucination Handling**: If the model returns invalid coordinates (e.g., lat > 90), missing required fields, or clearly hallucinated data — log the error with `logging.warning()`, skip that specific article, and continue processing the rest of the batch. **Never crash the pipeline** because of one bad LLM response.
   - **Translation**: The prompt must instruct the model to translate all event summaries into English by default, regardless of the source language.

5. **Storage (`geoalchemy2` + PostGIS)**:
   - Save the extracted, validated event data to PostGIS using GeoAlchemy2.
   - Store coordinates as PostGIS `GEOMETRY(Point, 4326)` columns.
   - Store affected regions as PostGIS `GEOMETRY(Polygon, 4326)` or `GEOMETRY(MultiPolygon, 4326)`.

### Prompt Management
- All GenAI prompts must be **version-controlled** in the codebase (e.g., stored as constants in `src/hermes_api/prompts/` or a similar module).
- This allows prompts to be unit-tested, diffed in code review, and tracked historically.
- Never hardcode prompts as inline strings in service functions.

---

## 3. Smart Editor Algorithm

The backend must implement a ranking algorithm so the frontend's initial load shows only the most critical events, not everything in the database. The algorithm considers:

- **Source Consensus**: Events reported by multiple independent RSS sources are ranked higher. If 10 different feeds mention the same event (detected via location + time proximity + topic similarity), it is more significant than an event from a single source.
- **Time Decay**: Recent events are weighted more heavily. An event from 1 hour ago outranks a similar event from 3 days ago. The decay function should be configurable.
- **Severity**: The AI-extracted severity level contributes to the ranking.

The API must expose this as a query parameter (e.g., `?min_score=0.7`) so the frontend can request only top-ranked events for the initial globe view and progressively load lower-ranked events as the user zooms in.

---

## 4. Database Architecture (PostGIS)

### Spatial Indexing
- **GIST indexes** must be created on all geometry columns (`location`, `target_location`, `affected_region`). Without these, spatial queries will perform full table scans and be unusable at scale.
- Use `ST_Intersects` with bounding box queries for viewport-based filtering. The frontend sends its current viewport as a bounding box (SW corner, NE corner), and the API returns only events within that box.

### Time-Series & Historical Data
- The system retains all historical events for playback (e.g., a time-slider on the frontend).
- Architect the database with **time-based table partitioning** (e.g., monthly partitions on `created_at`) to keep query performance stable as the dataset grows into millions of rows.
- Consider adding a `is_active` or `expires_at` column so stale events can be filtered out of the default "live" view without being deleted.

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

```
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
