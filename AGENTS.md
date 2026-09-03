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

---

## 2. Product Vision & Core Mechanics

Project Hermes is a real-time geospatial news aggregator designed to combat modern news fatigue by transforming traditional text-heavy feeds into a unified, interactive global map.

As an agent, you must design features that align with these core mechanics:

- **Dual-Mode Interface**: Users can seamlessly transition between a two-dimensional regional map and a three-dimensional geopolitical globe, allowing them to visually digest information at both local and macro scales.
- **Smart Editor Algorithm**: The application must not overwhelm the user with raw data. Instead, it relies on a backend algorithm that ranks news based on **source consensus** and **time decay**. The initial load must display only the most critical global events.
- **Dynamic Viewport Queries**: As users zoom into specific regions, the frontend must instantly query the spatial database to populate hyper-local news exactly within their viewport.
- **Visual Categorization**: Use color-coded pins to categorize events (e.g., economic shifts, conflicts). These pins must automatically cluster at higher zoom levels to prevent screen clutter.
- **Hybrid AI Geoparsing**: The system relies on an AI pipeline to extract *exact* physical coordinates from raw article text to ensure pinpoint accuracy on the map.
- **Geopolitical Nuance Visualization**: You must visually handle complex relationships. Use dynamic **relationship arcs** to illustrate intangible ties (like trade agreements or sanctions across the globe) and **territorial shading** to clearly depict ongoing states of conflict within national borders.

---

## 3. Architecture & Data Pipeline

**Crucial Note on Flexibility**: The pipeline described below is the *current* iteration. It is highly prone to change as newer and better approaches are discovered. You must remain flexible, actively thrive for better performant approaches, and not just blindly stick to this specific pipeline if a superior architecture exists.

### Backend Flow
- **Ingestion**: `apscheduler` runs background jobs -> `feedparser` fetches RSS feeds.
- **Deduplication**: Strict deduplication/caching layer (e.g., URL/hash checks) ensures we never send the exact same article to the LLM twice.
- **AI Extraction**: `google-genai` processes the text. You must enforce structured outputs (via Pydantic). If the model hallucinates, log the error gracefully, skip the event, and do not crash the pipeline. Translate event summaries into English by default.
- **Database**: Data is saved to PostGIS via `geoalchemy2`. 
- **Delivery**: FastAPI serves the processed data. The map data API is public but heavily rate-limited to prevent scraping. Any admin/ingestion routes must be strictly authenticated.

### Scalability & Data Handling
- **Scale**: Architect the system to comfortably handle 10,000+ active events simultaneously.
- **Spatial Queries**: Maximize PostGIS efficiency using spatial indexes (GIST) and bounding box queries (`ST_Intersects`).
- **Time-Series**: The system retains history for playback (e.g., a time-slider). Architect the database with time-series partitioning to handle growing historical data efficiently.

### Frontend Flow
- **State Management**: **Zustand** is the single source of truth for global state (loaded events, filters). Mapbox and React UI react to and update this store.
- **Map Rendering**: Prioritize Mapbox Native layers (GeoJSON sources, clustering, arc layers). Avoid rendering thousands of individual HTML/React DOM markers, as this destroys performance.
- **Real-Time Updates**: The architecture targets true real-time delivery via WebSockets or Server-Sent Events (SSE). 

---

## 4. UI/UX Design Language

- **Theme**: "Mission Control" / Tech-vibes.
- **Visual Elements**: Sleek dark-mode, translucent overlays (glassmorphism) over the map. Components and widgets must be completely squared with sharp edges.
- **Colors**: High-contrast colors (e.g., reds, ambers) to indicate event severity, alongside specific colors based on the event category.
- **Resilience**: Handle network disconnects gracefully with non-intrusive toast notifications or offline indicators, allowing users to interact with cached data rather than throwing full-screen blocking errors.
- **Accessibility (a11y)**: Pragmatic accessibility. All UI elements outside the map (sidebars, lists) must be fully accessible (ARIA, keyboard navigation). The WebGL map canvas is accepted as a visually dependent element.

---

## 5. Nx Monorepo Workflow & Mentorship

As an AI agent, you must act as a strict **Nx Monorepo Mentor** for the user. The user is actively learning Nx, so you must **stop them** and correct their approach if they violate any of the following conventions:

- **Root Execution Only**: You MUST interrupt the user if they try to `cd` into a child directory (like `apps/hermes/`) to run a script, or if they suggest running raw `npm run ...`. Insist that ALL commands be executed from the workspace root using `npx nx <target> <project>` (e.g., `npx nx serve hermes`) so that Nx's computation caching functions correctly.
- **Strict Generators**: Never create new UI components, libraries, or Python modules by manually adding files to the tree. You must **always** use Nx generators (e.g., `npx nx g @nx/react:component`, `npx nx g @nx/python:library`). This ensures that `project.json` configurations, TypeScript paths, and linting rules remain perfectly synchronized.
- **The 80/20 Rule (Apps vs Libs)**: `apps/` must remain thin and act primarily as routing and configuration shells. Most business logic, UI components, and API utilities must reside in shared libraries within the `libs/` directory (e.g., `libs/feature-map`, `libs/ui-widgets`). Warn the user if they attempt to build monolithic logic directly inside `apps/`.
- **Module Boundaries**: Actively help the user configure and enforce strict architectural boundary tags in `project.json` (e.g., `type:feature`, `type:ui`, `scope:map`). Rely on ESLint (`@nx/enforce-module-boundaries`) to prevent circular dependencies or architectural violations (like a "dumb" UI component importing a "smart" feature library).
- **Shared Types**: Store TypeScript interfaces for API responses in a dedicated Nx library (e.g., `libs/shared-types`) to share between the Python backend schemas and frontend consumers.

---

## 6. Development Best Practices

- **Prompts**: Google GenAI prompts must be version-controlled (e.g., stored as constants in `src/prompts/`) so they can be unit-tested and tracked.
- **Environment Variables**: Fail-fast and be type-safe. Use `pydantic-settings` in Python and Vite's strict env typing in React. If a required secret is missing, the app must crash on startup with a clear error message.
- **Observability**: Implement structured JSON logging in the backend (Python `logging`) and a centralized logging utility in the frontend.
