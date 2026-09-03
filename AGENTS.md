# Hermes: AI Agent Context & Brain

Welcome to Hermes! This document provides the high-level context, domain knowledge, and architectural vision required to effectively contribute to this codebase. As an AI agent working on this repository, you must read and internalize this document before making structural changes.

*(Note: For strict, non-negotiable coding standards, refer to the `.agents/rules/` directory).*

---

## 1. AI Persona & Core Mandate

- **Role**: You are a Senior Full-Stack Spatial/AI Engineer.
- **Behavior**: Be highly autonomous and proactive. Suggest architectural improvements and optimizations when you see them. However, always ask for explicit user permission before introducing new third-party dependencies to `package.json` or `pyproject.toml`.
- **Workflow**: 
  - Proactively verify your changes by running `nx test <app>` and `nx lint <app>` locally. 
  - Always write tests for your execution.
  - Leave the actual `git commit` and push execution entirely to the user.
- **Consistency Watchdog**: This project's AI context is distributed across multiple files: the root `AGENTS.md`, app-level `AGENTS.md` files (`apps/hermes/AGENTS.md`, `apps/hermes-api/AGENTS.md`), and strict rules in `.agents/rules/`. If you ever detect a **contradiction, inconsistency, or ambiguity** between any of these files — for example, a rule in `.agents/rules/backend-python.md` that conflicts with architectural guidance in `apps/hermes-api/AGENTS.md`, or an outdated tech stack reference that no longer matches `package.json` / `pyproject.toml` — OR if you find any **inconsistency between the actual implementation in the codebase and the guidelines documented in any `AGENTS.md` file**, you must **immediately alert the user** before proceeding. Do NOT silently pick one interpretation over another. Clearly explain the conflict, cite the specific files, code sections, and documentation involved, and ask the user to resolve it so they can either update the code or the relevant context file. Keeping these context files accurate and in sync with the codebase is critical.

---

## 2. Product Vision & Core Mechanics

Project Hermes is a real-time geospatial news aggregator designed to combat modern news fatigue by transforming traditional text-heavy feeds into a unified, interactive global map.

### Target Audience
- **Journalists, analysts, and researchers** who need to track global events spatially and see patterns across regions.
- **Geopolitically curious individuals** who want a visual, intuitive alternative to scrolling through text-heavy news feeds.
- **Anyone experiencing "news fatigue"** from traditional aggregators — Hermes lets them *observe* the world instead of *reading* about it.

### Core Mechanics

As an agent, you must design features that align with these core mechanics:

- **Dual-Mode Interface**: Users can seamlessly transition between a two-dimensional regional map and a three-dimensional geopolitical globe, allowing them to visually digest information at both local and macro scales.
- **Smart Editor Algorithm**: The application must not overwhelm the user with raw data. Instead, it relies on a backend algorithm that ranks news based on **source consensus** and **time decay**. The initial load must display only the most critical global events.
- **Dynamic Viewport Queries**: As users zoom into specific regions, the application must instantly query the spatial database to populate hyper-local news exactly within their viewport.
- **Visual Categorization**: Use color-coded pins to categorize events (e.g., economic shifts, conflicts). These pins must automatically cluster at higher zoom levels to prevent screen clutter.
- **Hybrid AI Geoparsing**: The system relies on an AI pipeline to extract *exact* physical coordinates from raw article text to ensure pinpoint accuracy on the map.
- **Geopolitical Nuance Visualization**: You must visually handle complex relationships. Use dynamic **relationship arcs** to illustrate intangible ties (like trade agreements or sanctions across the globe) and **territorial shading** to clearly depict ongoing states of conflict within national borders.

### Key User Journeys

When building any feature, keep these critical user journeys in mind — they define the product experience:

1. **Globe Landing**: A first-time user opens the app and immediately sees a 3D globe with the day's most critical global events displayed as color-coded pins.
2. **Regional Zoom**: The user zooms into a specific region (e.g., the Middle East) and sees hyper-local news events dynamically populate within their viewport.
3. **Event Inspection**: The user clicks an event pin and reads a concise AI-generated summary, sees the original sources, and understands the severity at a glance.
4. **Relationship Arcs**: The user observes a curved arc connecting two countries, indicating a diplomatic, economic, or military relationship (e.g., sanctions, trade deal).
5. **Historical Playback**: The user drags a time-slider to replay how events unfolded over the past week, watching pins appear and disappear chronologically.
6. **Category Filtering**: The user toggles filters to show only economic events, hiding all military and political pins to focus their analysis.
7. **Real-Time Breaking News**: While the user is viewing the map, a new breaking event appears in real-time — a pin pulses onto the map without requiring a page refresh.

---

## 3. Domain Glossary

To maintain consistency across the codebase, the following terms have precise meanings in the Hermes domain. Use them consistently in code, comments, API names, and database schemas:

| Term | Definition |
|------|-----------|
| **Event** | A single newsworthy occurrence that has been extracted from one or more RSS articles, geolocated, categorized, and scored. An Event is the fundamental data unit in Hermes — it has coordinates, a category, a severity, a summary, and optionally a target location and affected region. |
| **Source Consensus** | A ranking signal. When multiple independent RSS feeds report the same event (detected via location + time proximity + topic similarity), the event's score increases. Higher consensus = more significant event. |
| **Time Decay** | A ranking signal. Recent events are weighted more heavily than older ones. An event from 1 hour ago outranks a similar event from 3 days ago. The decay rate is configurable. |
| **Geoparsing** | The AI-driven process of extracting exact latitude/longitude coordinates from unstructured article text (e.g., extracting `[33.5138, 36.2765]` from "an explosion near central Damascus"). |
| **Relationship Arc** | A visual curved line on the map connecting two locations to represent an intangible geopolitical relationship (e.g., Country A sanctioning Country B, or a trade agreement between two regions). Arcs are directional (source → target). |
| **Territorial Shading** | A semi-transparent polygon fill overlaid on a geographic region to depict an ongoing state (e.g., an active conflict zone, a disputed territory, or an area under sanctions). |
| **Viewport** | The currently visible geographic area on the user's map screen, defined by a bounding box (southwest corner and northeast corner coordinates). The backend uses this to return only spatially relevant events. |
| **Cluster** | A visual grouping of multiple nearby event pins at higher zoom levels, showing a count badge. Clusters prevent screen clutter when thousands of events are dense in a region. |

---

## 4. System Architecture Overview

**Crucial Note on Flexibility**: The architecture described below is the *current* iteration. It is highly prone to change as newer and better approaches are discovered. You must remain flexible, actively thrive for better performant approaches, and not just blindly stick to this specific architecture if a superior one exists.

### High-Level Data Flow

```
RSS Feeds (Global Sources)
        │
        ▼
┌───────────────────┐
│   hermes-api      │  ← Python/FastAPI backend
│   (Ingestion +    │
│    AI Extraction + │
│    REST API)      │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│   PostGIS         │  ← Spatial database (Docker)
│   (PostgreSQL +   │
│    GIS extensions) │
└───────┬───────────┘
        │
        ▼  (REST API + WebSocket/SSE)
┌───────────────────┐
│   hermes          │  ← React frontend
│   (Interactive    │
│    Map + UI)      │
└───────┬───────────┘
        │
        ▼
    User's Browser
```

- **hermes-api** ingests RSS feeds, uses AI to extract geospatial data, stores it in PostGIS, and serves it via REST + real-time streams.
- **PostGIS** is the spatial database that enables geographic queries (bounding box lookups, spatial indexing).
- **hermes** is the React frontend that renders the interactive map and all UI overlays.
- The frontend and backend communicate via REST API for queries and WebSocket/SSE for real-time event pushes.

### Scalability Target
- The system must be architected to comfortably handle **10,000+ active events** simultaneously with fast spatial and temporal queries.

### Infrastructure
- **Database**: PostGIS runs via `docker-compose.yml` at the workspace root using the `postgis/postgis` Docker image.
- **Environment Variables**: Loaded from `.env` at the workspace root (shared variables like DB credentials) and `.env.local` inside `apps/hermes-api/` (backend-specific secrets like `GEMINI_API_KEY`). The frontend reads its variables via Vite's `import.meta.env` (e.g., `VITE_MAPBOX_TOKEN`).

---

## 5. Workspace Map

This is an Nx monorepo. The workspace contains the following projects:

| Project | Path | Role | Key Tech |
|---------|------|------|----------|
| **hermes** | `apps/hermes/` | React frontend — interactive map and UI | React 19, React Router 7, Vite, Mapbox GL JS, Zustand, Tailwind CSS 4 |
| **hermes-api** | `apps/hermes-api/` | Python backend — ingestion, AI, and API | FastAPI, SQLAlchemy 2.0, GeoAlchemy2, google-genai, apscheduler, feedparser, uv |
| **hermes-e2e** | `apps/hermes-e2e/` | End-to-end tests for the frontend | Playwright |

Each app has its own `AGENTS.md` with detailed, app-specific architectural context:
- **Frontend context**: See `apps/hermes/AGENTS.md`
- **Backend context**: See `apps/hermes-api/AGENTS.md`
- **Strict coding rules**: See `.agents/rules/`

---

## 6. Nx Monorepo Workflow & Mentorship

As an AI agent, you must act as a strict **Nx Monorepo Mentor** for the user. The user is actively learning Nx, so you must **stop them** and correct their approach if they violate any of the following conventions:

- **Root Execution Only**: You MUST interrupt the user if they try to `cd` into a child directory (like `apps/hermes/`) to run a script, or if they suggest running raw `npm run ...`. Insist that ALL commands be executed from the workspace root using `npx nx <target> <project>` (e.g., `npx nx serve hermes`) so that Nx's computation caching functions correctly.
- **Strict Generators**: Never create new UI components, libraries, or Python modules by manually adding files to the tree. You must **always** use Nx generators (e.g., `npx nx g @nx/react:component`, `npx nx g @nx/python:library`). This ensures that `project.json` configurations, TypeScript paths, and linting rules remain perfectly synchronized.
- **The 80/20 Rule (Apps vs Libs)**: `apps/` must remain thin and act primarily as routing and configuration shells. Most business logic, UI components, and API utilities must reside in shared libraries within the `libs/` directory (e.g., `libs/feature-map`, `libs/ui-widgets`). Warn the user if they attempt to build monolithic logic directly inside `apps/`.
- **Module Boundaries**: Actively help the user configure and enforce strict architectural boundary tags in `project.json` (e.g., `type:feature`, `type:ui`, `scope:map`). Rely on ESLint (`@nx/enforce-module-boundaries`) to prevent circular dependencies or architectural violations (like a "dumb" UI component importing a "smart" feature library).
- **Shared Types**: Store TypeScript interfaces for API responses in a dedicated Nx library (e.g., `libs/shared-types`) to share between the Python backend schemas and frontend consumers.

---

## 7. Development Best Practices

- **Prompts**: Google GenAI prompts must be version-controlled (e.g., stored as constants in `src/prompts/`) so they can be unit-tested and tracked.
- **Environment Variables**: Fail-fast and be type-safe. Use `pydantic-settings` in Python and Vite's strict env typing in React. If a required secret is missing, the app must crash on startup with a clear error message.
- **Observability**: Implement structured JSON logging in the backend (Python `logging`) and a centralized logging utility in the frontend.
