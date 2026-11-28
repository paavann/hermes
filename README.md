# Hermes: Real-Time Geospatial News Intelligence

[![Live Demo](https://img.shields.io/badge/Demo-hermes--eight--inky.vercel.app-00DC82?style=flat&logo=vercel&logoColor=white)](https://hermes-eight-inky.vercel.app)
[![Nx Monorepo](https://img.shields.io/badge/Nx-23.2-143055?style=flat&logo=nx&logoColor=white)](https://nx.dev)
[![React 19](https://img.shields.io/badge/React-19.2-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![React Router 8](https://img.shields.io/badge/React_Router-8.3-CA4245?style=flat&logo=react-router&logoColor=white)](https://reactrouter.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?style=flat&logo=postgresql&logoColor=white)](https://postgis.net)
[![pgvector](https://img.shields.io/badge/pgvector-halfvec(2048)-blue?style=flat)](https://github.com/pgvector/pgvector)
[![Langfuse](https://img.shields.io/badge/Observability-Langfuse-EE5E2A?style=flat&logo=langfuse&logoColor=white)](https://langfuse.com)
[![Mapbox GL JS](https://img.shields.io/badge/Mapbox_GL-v3.29-4264FB?style=flat&logo=mapbox&logoColor=white)](https://docs.mapbox.com/mapbox-gl-js/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Hermes is a real-time geospatial intelligence engine that transforms fragmented global news feeds into a unified, spatially grounded situational map. Instead of parsing repetitive text feeds, users observe events unfolding across the globe, corroborated across international sources and traced back to their historical roots.

**Live Application**: [hermes-eight-inky.vercel.app](https://hermes-eight-inky.vercel.app)

---

## Overview

Traditional news aggregators suffer from narrative duplication, click-driven recency bias, and a lack of physical geographic context. Hermes addresses this through an automated, multi-stage processing pipeline:

1. **Autonomous Ingestion & Labeling**: Fetches articles across global RSS/Atom wire services, news sitemaps, Google News fallbacks, and GDELT (`ingest-articles`), then transiently fetches full text and extracts structured claims, entities, and locations.
2. **Syndication Families & Incident Clustering**: Embeds claims (`halfvec(2048)`), groups wire reprints into syndication families so duplicate wires never inflate corroboration, and clusters articles into physical incident events (`CLUSTER` + `RECONCILE`).
3. **Verified Geocoding**: Extracts locations and key actor home cities via LLM and grounds coordinates strictly using OpenStreetMap Nominatim with token-bucket rate limiting and negative caching.
4. **Objective Ranking**: Computes one explainable `importance_score` (0–100, `score-v2`) from independent-family strength, impact level, verification status, and reporting quality with impact-tiered exponential decay, single-source capping (`65`), and hysteresis visibility tiers (`PRIMARY` / `FILLER` / `DROP`).
5. **Relationships, Story Threads & Causality Timelines**: Discovers typed cross-event relationships (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`), links developing story threads, and reconstructs historical antecedent DAGs via Wikipedia (`POST /api/v1/events/tl/{id}`).
6. **Grounded Conversational RAG**: Answers analyst questions over live map context or the globe with hybrid lexical/semantic retrieval, optional Tavily web search, inline citations, PostgreSQL-backed (with in-memory fallback) conversation checkpoints, and Server-Sent Events streaming.

> [!NOTE]
> Detailed system architecture diagrams, data pipelines, and design decisions are documented in [docs/architecture.md](docs/architecture.md).

---

## Core Capabilities

- **Interactive Tactical Map**: Full-screen WebGL map engine built on Mapbox GL JS with GPU layer clustering, cross-event relationship arcs and actor vectors (`/api/v1/events/relationships`), dynamic bounding-box synchronization (`/api/v1/events/bbox`), cluster drill-down, story thread drawers, and camera transitions.
- **Editorial Consensus & Reconciliation Engine**: Corroborates independent reporting families into single incident pins (`CONFIRMED`, `CORROBORATED`, `SINGLE_SOURCE`, `CONFLICTING`) and merges duplicate incidents non-destructively via redirect chains.
- **Historical Causality DAGs & Threads**: On-demand timeline synthesis (`/api/v1/events/tl/{id}`) connecting breaking incidents to Wikipedia historical milestones alongside multi-event story thread narratives (`/api/v1/threads/{id}`).
- **Grounded Chat**: Context-aware conversational answers (`POST /api/v1/chat`) streamed over SSE, with hybrid retrieval, optional Tavily web search, and citations that focus the map.
- **Traceability & Observability**: Integrated with [Langfuse](https://langfuse.com) for span tracking, content masking, token accounting, latency monitoring, and model fallback observability across batch ingestion and on-demand synthesis.
- **Resilient Pipeline**: Token-bucket rate limiting, circuit breaking, SSRF-safe transient fetching, and schema-level LLM fallback extractors prevent failures during external API degradation.

---

## Workspace Structure

Hermes is configured as an Nx polyglot monorepo combining TypeScript and Python workspaces (`uv`):

```text
hermes/
├── apps/
│   ├── hermes/            # React 19 + React Router v8 SSR frontend
│   ├── hermes-api/        # FastAPI REST API service
│   ├── hermes-worker/     # Batch CLI ingestion and lifecycle worker
│   └── hermes-e2e/        # Playwright end-to-end test suite
├── libs/
│   ├── chat/              # Conversational RAG client (SSE, citations, Zustand store)
│   ├── map/               # Mapbox GL JS WebGL map engine & Zustand store
│   └── shared/
│       ├── hermes-ai/     # LiteLLM extraction, chat engine, embeddings & geocoding
│       ├── hermes-db/     # SQLAlchemy 2.0 models, PostGIS & pgvector HNSW
│       ├── ui-components/ # Shared HUD components (Tailwind CSS v4)
│       ├── util-types/    # Hand-mirrored TypeScript API contracts
│       └── utils/         # Shared Python (py) and TypeScript (ts) helpers
└── docs/
    └── architecture.md    # In-depth architectural specifications & diagrams
```

### Component Breakdown

| Project | Type | Description |
| :--- | :--- | :--- |
| [`@hermes/hermes`](apps/hermes/README.md) | Web Client | SSR React 19 application with Clerk authentication and Mapbox WebGL viewport. |
| [`hermes-api`](apps/hermes-api/README.md) | REST API | FastAPI application serving spatial queries, timeline synthesis, and streaming chat. |
| [`hermes-worker`](apps/hermes-worker/README.md) | Batch CLI | Ephemeral run-and-die container orchestrating feed sync and lifecycle decay. |
| [`@hermes/chat`](libs/chat/README.md) | Library | Chat overlay, SSE transport, citation parsing, and persisted conversation store. |
| [`@hermes/map`](libs/map/README.md) | Library | Mapbox GL JS engine, Zustand viewport state, and timeline drawer components. |
| [`hermes-ai`](libs/shared/hermes-ai/README.md) | Library | LLM extraction via LiteLLM, rate-limited Nominatim geocoding, and embeddings. |
| [`hermes-db`](libs/shared/hermes-db/README.md) | Library | PostGIS geometry, `halfvec(2048)` pgvector tables, and Alembic migrations. |
| [`@hermes/ui-components`](libs/shared/ui-components/README.md) | Library | Reusable design system primitives adhering to the HUD monospace aesthetic. |
| [`@hermes/util-types`](libs/shared/util-types/README.md) | Library | TypeScript response types synchronized with API Pydantic schemas. |

---

## Getting Started

### Prerequisites

- **Node.js**: `22.x` or later
- **Python**: `3.14` or later
- **uv**: Modern Python package and project manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Docker**: For running PostGIS with `pgvector`
- **Mapbox Account**: Public access token for WebGL map tiles

### Installation & Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/hermes.git
   cd hermes
   ```

2. **Install monorepo dependencies**:
   ```bash
   npm ci && uv sync
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Ensure your `.env` contains database settings, Clerk authentication keys (`apps/hermes/.env` holds Vite client `VITE_*` variables per `apps/hermes/vite.config.mts`), and your Mapbox public token. For LLM capabilities, configure `LLM_API` and `EMBED_API` in `apps/hermes-api/.env.local` (and `apps/hermes-worker/.env.local`); chat additionally reads `CHAT_*` and optional `TAVILY_API_KEY` settings. To enable Langfuse trace observability, add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`.

4. **Start the local database**:
   ```bash
   docker compose up -d hermes-db
   ```

5. **Run database migrations**:
   ```bash
   npx nx run hermes-db:migrate
   ```

6. **Start the development servers**:
   ```bash
   # Terminal 1: Backend API (http://localhost:8000)
   npx nx serve hermes-api

   # Terminal 2: Frontend client (http://localhost:4200)
   npx nx dev hermes
   ```

7. **(Optional) Run the worker pipeline**:
   ```bash
   # Ingest feeds and label/embed articles
   npx nx run hermes-worker:ingest-articles

   # Cluster events, synthesize descriptions/actors, score, merge, link, and thread
   npx nx run hermes-worker:build-events

   # Requeue abandoned article claims and apply event/thread lifecycle transitions
   npx nx run hermes-worker:maintain-events
   ```

---

## Testing & Quality Assurance

All packages are validated through automated linting and test suites:

```bash
# Run linting across TypeScript (ESLint) and Python (Ruff)
npm run lint

# Run all test suites (Vitest for frontend/libs, Pytest for backend/worker/libs)
npm test

# Run type checks
npx nx affected -t typecheck --base=master
```

---

## Documentation

- [**Architecture Guide**](docs/architecture.md): System components, data pipelines, ranking algorithms, and deployment topology.
- [**Application Guides**]:
  - [Frontend Web App](apps/hermes/README.md)
  - [FastAPI Service](apps/hermes-api/README.md)
  - [Worker CLI Ingestion Engine](apps/hermes-worker/README.md)
- [**Library Guides**]:
  - [Map Engine & Visualization](libs/map/README.md)
  - [Conversational Chat Client](libs/chat/README.md)
  - [AI & Geocoding Services](libs/shared/hermes-ai/README.md)
  - [Database Schemas & Models](libs/shared/hermes-db/README.md)
  - [UI Component Library](libs/shared/ui-components/README.md)
  - [TypeScript Contracts](libs/shared/util-types/README.md)

---

## License

This project is licensed under the [MIT License](LICENSE).
