# Hermes: AI Agent Context & Brain

Welcome to Hermes! This document provides the high-level context, domain knowledge, and architectural vision required to effectively contribute to this codebase. As an AI agent working on this repository, you must read and internalize this document before making structural changes.

_(Note: For strict, non-negotiable coding standards, refer to the `.agents/rules/` directory and project-level `.agents/rules/` files)._

---

## 1. AI Persona & Core Mandate

- **Role**: You are a Senior Full-Stack Spatial/AI Engineer.
- **Behavior**: Be highly autonomous and proactive. Suggest architectural improvements and optimizations when you see them. However, always ask for explicit user permission before introducing new third-party dependencies to `package.json` or `pyproject.toml`.
- **Workflow**:
  - Proactively verify your changes by running `npx nx test <project>` and `npx nx lint <project>` locally.
  - Always write tests for your execution.
  - Leave the actual `git commit` and push execution entirely to the user.
- **Consistency Watchdog**: This project's AI context is distributed across multiple files: the root `AGENTS.md`, app-level `AGENTS.md` files (`apps/hermes/AGENTS.md`, `apps/hermes-api/AGENTS.md`), and strict rules in `.agents/rules/`. If you ever detect a **contradiction, inconsistency, or ambiguity** between any of these files — for example, a rule in `.agents/rules/` that conflicts with architectural guidance in `apps/hermes-api/AGENTS.md`, or an outdated tech stack reference that no longer matches `package.json` / `pyproject.toml` — OR if you find any **inconsistency between the actual implementation in the codebase and the guidelines documented in any `AGENTS.md` file**, you must **immediately alert the user** before proceeding. Do NOT silently pick one interpretation over another. Clearly explain the conflict, cite the specific files, code sections, and documentation involved, and ask the user to resolve it so they can either update the code or the relevant context file. Keeping these context files accurate and in sync with the codebase is critical.

---

## 2. Product Vision & Core Mechanics

Project Hermes is a real-time geospatial news aggregator designed to combat modern news fatigue by transforming traditional text-heavy feeds into a unified, interactive global map.

### Target Audience

- **Journalists, analysts, and researchers** who need to track global events spatially and see patterns across regions.
- **Geopolitically curious individuals** who want a visual, intuitive alternative to scrolling through text-heavy news feeds.
- **Anyone experiencing "news fatigue"** from traditional aggregators — Hermes lets them _observe_ the world instead of _reading_ about it.

### Core Mechanics

As an agent, you must design features that align with these core mechanics:

- **Dual-Mode Interface**: Users can seamlessly transition between a two-dimensional regional map and a three-dimensional geopolitical globe, allowing them to visually digest information at both local and macro scales.
- **Smart Editor Algorithm**: The application must not overwhelm the user with raw data. Instead, it relies on a backend algorithm that ranks news based on **source consensus** and **time decay**. The initial load displays only the most critical global events.
- **Dynamic Viewport Queries**: As users zoom into specific regions, the application queries the spatial database to populate hyper-local news within their bounding box.
- **Visual Categorization**: Use color-coded pins to categorize events (e.g., economic shifts, conflicts). Pins automatically cluster at higher zoom levels via WebGL to prevent screen clutter.
- **Hybrid Geoparsing & Geocoding**: The system uses an AI pipeline to extract location _names_ from raw article text, which are then passed through a dedicated geocoding service (Nominatim) backed by a PostgreSQL cache. This eliminates AI coordinate hallucinations and ensures pinpoint map accuracy.
- **Historical Causality (Timeline Engine)**: Users can inspect an event and open an interactive timeline drawer (`TlPanel`) to observe causal antecedents, Wikipedia historical context, and map camera hops across historical milestones culminating in today's active event.

### Key User Journeys

When building any feature, keep these critical user journeys in mind:

1. **Globe Landing**: A first-time user opens the app, watches the tactical boot sequence, and immediately sees the day's most critical global events displayed as color-coded pins.
2. **Regional Zoom**: The user zooms into a specific region (e.g., the Middle East) and sees hyper-local news events dynamically populate within their viewport.
3. **Event Inspection**: The user clicks an event pin, centers the camera smoothly, reads a concise AI-generated summary with a terminal scramble-text decode, and sees original news sources.
4. **Historical Timeline Investigation**: The user opens the timeline panel to trace the historical roots of the event via a causal graph (MediaWiki extracts linked to the current incident).
5. **Category Filtering**: The user toggles filters to focus on specific domains (Economy, Conflict, Politics, Technology, etc.).
6. **Real-Time Breaking News**: When the ingestion pipeline discovers breaking news, new events appear on the map dynamically.

---

## 3. Domain Glossary

To maintain consistency across the codebase, the following terms have precise meanings in the Hermes domain:

| Term | Definition |
| :--- | :--- |
| **Event** | A single newsworthy occurrence extracted from one or more RSS articles, geolocated, categorized, and scored. An Event is the fundamental data unit in Hermes — it has coordinates (`POINT`, SRID 4326), a category, a category color, a summary, a trending score, and an embedding vector. |
| **Source Consensus** | A ranking signal. When multiple independent RSS feeds report the same event (detected via semantic vector similarity using `pgvector` half-precision embeddings and confirmed by the LLM), the event's score increases according to the source credibility tiers. |
| **Credibility Tier** | A weighting tier assigned to news sources (`TIER_1` = +3.0, `TIER_2` = +2.0, `TIER_3` = +1.0, `TIER_4` = +0.5) that determines how much weight an article adds to an event's trending score. |
| **Time Decay** | A ranking signal. Recent events are weighted more heavily than older ones. An hourly lifecycle background job applies a strict -10% decay to all active trending scores so that old news organically drops down the rankings over 24–48 hours. |
| **Geoparsing** | The process of extracting a geographic location name from unstructured article text (e.g., 'Geneva, Switzerland') via AI, and subsequently resolving it to exact latitude/longitude coordinates using a geocoding service backed by `geocode_cache`. |
| **Historical Timeline (Lineage)** | A synthesized causal graph (`event_timelines`) connecting historical Wikipedia milestones through causal verbs (`"led to"`, `"triggered"`) to the current active event. |
| **Viewport** | The currently visible geographic area on the user's map screen, defined by a bounding box (`north`, `south`, `east`, `west`). The backend uses this to return only spatially relevant events via `ST_Within`. |
| **Cluster** | A visual WebGL grouping of multiple nearby event pins at higher zoom levels, showing a count badge. Clusters prevent screen clutter when thousands of events are dense in a region. |

---

## 4. System Architecture Overview

**Crucial Note on Flexibility**: The architecture described below is the _current_ iteration. You must remain flexible, actively seek performant approaches, and not blindly stick to this specific architecture if a superior one exists.

### High-Level Data Flow

```text
RSS Feeds (Global Sources)
        │
        ▼
┌───────────────────┐
│   hermes-api      │  ← Python/FastAPI backend
│   (Ingestion +    │     - LiteLLM Multi-Model Router (Mistral + NVIDIA NIM fallback)
│    Embeddings +   │     - 2048-dim Embeddings (nemotron-3-embed-1b)
│    Nominatim +    │     - Grounded Geocoding (Nominatim + GeocodeCache)
│    Timeline Svc)  │     - APScheduler Dynamic Cadence & Decay Jobs
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│   PostGIS         │  ← Spatial & Vector database (Docker)
│   (PostgreSQL 16  │     - Point Geometry (SRID 4326) with GIST Index
│    + PostGIS      │     - pgvector halfvec(2048) with HNSW Index
│    + pgvector)    │     - JSONB Historical Timeline Nodes & Edges
└───────┬───────────┘
        │
        ▼  (REST API: /api/v1/events, /api/v1/events/bbox, /api/v1/events/tl)
┌───────────────────┐
│   hermes          │  ← React 19 Frontend Shell
│   (Mapbox GL JS + │     - Native WebGL Layer Rendering & Clustering
│    Zustand +      │     - Zustand Global Map Telemetry Store
│    TanStack Query │     - TanStack Query v5 Viewport Sync & Polling
│    + Mission HUD) │     - Mission Control UI (Zero Border Radius, Monospace)
└───────┬───────────┘
        │
        ▼
    User's Browser
```

### Scalability Target

- The system must be architected to comfortably handle **10,000+ active events** simultaneously with fast spatial (`ST_Within`) and vector (`halfvec_cosine_ops`) queries.

### Infrastructure

- **Database**: PostGIS runs via `docker-compose.yml` at the workspace root using a custom build based on `postgis/postgis` with `postgresql-$PG_MAJOR-pgvector` installed inline.
- **Environment Variables**: Loaded from `.env` at the workspace root (shared variables like DB credentials, ports, Mapbox token) and `.env.local` inside `apps/hermes-api/` (backend keys like `LLM_API`, `LLM_MODEL`, `EMBED_API`, `EMBED_MODEL`). The frontend reads its variables via Vite's `import.meta.env` (e.g., `VITE_MAPBOX_TOKEN`, `VITE_BASE_URL`, `VITE_API_VER`).

---

## 5. Workspace Map

This is an Nx monorepo. The workspace contains the following projects:

| Project | Path | Role | Key Tech |
| :--- | :--- | :--- | :--- |
| **`hermes`** | `apps/hermes/` | React frontend shell — interactive map and HUD | React 19, React Router 8 (SPA mode), Vite, Mapbox GL JS v3, Zustand 5, TanStack Query v5, Tailwind CSS 4 |
| **`hermes-api`** | `apps/hermes-api/` | Python backend — ingestion, AI, and REST API | FastAPI, SQLAlchemy 2.0 Async, PostGIS, pgvector (`halfvec`), LiteLLM, APScheduler, feedparser, uv |
| **`hermes-e2e`** | `apps/hermes-e2e/` | End-to-end browser tests | Playwright |
| **`@hermes/feature-map`** | `libs/feature-map/` | Mapbox GL WebGL implementation & timeline drawer | Mapbox GL JS, Zustand store, TanStack Query hooks, `MapView`, `EventPopup`, `TlPanel` |
| **`@hermes/ui-components`** | `libs/shared/ui-components/`| Tactical Mission Control HUD widgets | React 19, Tailwind CSS 4, `BootSequence`, `LiveClock` |
| **`@hermes/util-types`** | `libs/shared/util-types/` | Shared TypeScript API response interfaces | TypeScript interfaces (`MapEventResponse`, `EventDetailResponse`, `TlResponse`) |
| **`@hermes/utils`** | `libs/shared/utils/` | Cross-cutting shared utility helpers | TypeScript |

Each app has its own `AGENTS.md` and `README.md` with detailed, app-specific architectural context:

- **Frontend context**: See `apps/hermes/AGENTS.md` and `apps/hermes/README.md`
- **Backend context**: See `apps/hermes-api/AGENTS.md` and `apps/hermes-api/README.md`
- **Strict coding rules**: See `.agents/rules/`

---

## 6. Nx Monorepo Workflow & Mentorship

As an AI agent, you must act as a strict **Nx Monorepo Mentor** for the user. Correct their approach if they violate any of the following conventions:

- **Root Execution Only**: ALL commands must be executed from the workspace root using `npx nx <target> <project>` (e.g., `npx nx serve hermes`, `npx nx serve hermes-api`). Never `cd` into child directories to run scripts.
- **Strict Generators**: Never create new UI components, libraries, or Python modules by manually adding files to the tree. Always use Nx generators (e.g., `npx nx g @nx/react:component`, `npx nx g @nx/python:library`) so paths and configs remain synchronized.
- **The 80/20 Rule (Apps vs Libs)**: `apps/` must remain thin and act primarily as routing and configuration shells. Most business logic, UI components, and API utilities must reside in shared libraries within the `libs/` directory (`libs/feature-map`, `libs/shared/ui-components`, `libs/shared/util-types`). Warn the user if they attempt to build monolithic logic directly inside `apps/`.
- **Module Boundaries**: Configure and enforce strict architectural boundary tags in `project.json` (e.g., `type:app`, `scope:frontend`). Rely on ESLint (`@nx/enforce-module-boundaries`) to prevent circular dependencies or architectural violations.
- **Shared Types**: Store TypeScript interfaces for API responses in a dedicated library (`libs/shared/util-types`) to keep contracts aligned between backend schemas and frontend consumers.

---

## 7. Development Best Practices

- **Prompts**: Prompts must be version-controlled in the codebase and structured for strict JSON schema outputs.
- **Environment Variables**: Fail-fast and be type-safe. Use `pydantic-settings` in Python and Vite's strict env typing in React. If a required secret is missing, the app must crash on startup with a clear error message. Never provide silent default fallbacks for security credentials.
- **Observability**: Implement structured logging in the backend (Python `logging`) and centralized logging utilities in the frontend.
