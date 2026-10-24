# Hermes: Real-Time Geospatial News Intelligence

[![Live Demo](https://img.shields.io/badge/Demo-hermes--eight--inky.vercel.app-00DC82?style=flat&logo=vercel&logoColor=white)](https://hermes-eight-inky.vercel.app)
[![Nx Monorepo](https://img.shields.io/badge/Nx-23.2-143055?style=flat&logo=nx&logoColor=white)](https://nx.dev)
[![React 19](https://img.shields.io/badge/React-19.2-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![React Router 8](https://img.shields.io/badge/React_Router-8.3-CA4245?style=flat&logo=react-router&logoColor=white)](https://reactrouter.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?style=flat&logo=postgresql&logoColor=white)](https://postgis.net)
[![pgvector](https://img.shields.io/badge/pgvector-halfvec(2048)-blue?style=flat)](https://github.com/pgvector/pgvector)
[![Mapbox GL JS](https://img.shields.io/badge/Mapbox_GL-v3.29-4264FB?style=flat&logo=mapbox&logoColor=white)](https://docs.mapbox.com/mapbox-gl-js/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Hermes is a real-time geospatial intelligence engine that transforms fragmented global news feeds into a unified, spatially grounded situational map. Instead of parsing repetitive text feeds, users observe events unfolding across the globe, corroborated across international sources and traced back to their historical roots.

**Live Application**: [hermes-eight-inky.vercel.app](https://hermes-eight-inky.vercel.app)

---

## Overview

Traditional news aggregators suffer from narrative duplication, click-driven recency bias, and a lack of physical geographic context. Hermes addresses this through an automated, multi-stage processing pipeline:

1. **Autonomous Ingestion**: Ingests articles across global wire services, major outlets, and GDELT.
2. **Vector Deduplication & Clustering**: Generates high-dimensional embeddings (`halfvec(2048)`) and uses HNSW index cosine distance to match incoming articles to active events.
3. **Verified Geocoding**: Extracts locations via LLM and grounds coordinates strictly using OpenStreetMap Nominatim with token-bucket rate limiting and negative caching.
4. **Objective Ranking**: Ranks events using source credibility tiers, impact multipliers, Shannon diversity across geopolitical blocs, reporting velocity, and compound time decay (18-hour half-life).
5. **Causal Timeline Synthesis**: Reconstructs the historical context of any breaking story by querying Wikipedia and generating an interactive antecedent timeline DAG.

> [!NOTE]
> Detailed system architecture diagrams, data pipelines, and design decisions are documented in [docs/architecture.md](docs/architecture.md).

---

## Core Capabilities

- **Interactive Tactical Map**: Full-screen WebGL map engine built on Mapbox GL JS with GPU canvas layer clustering, dynamic bounding-box synchronization (`/api/v1/events/bbox`), and camera transitions.
- **Editorial Consensus Engine**: Corroborates multiple independent reports into single unified events, tracking sources and syndication factors.
- **Historical Causality DAGs**: On-demand timeline synthesis (`/api/v1/events/tl/{id}`) that connects today's events to historical milestones extracted from Wikipedia.
- **Resilient Pipeline**: Token-bucket rate limiting, circuit breaking, and schema-level LLM fallback extractors prevent failures during external API degradation.

---

## Workspace Structure

Hermes is configured as an Nx polyglot monorepo combining TypeScript and Python workspaces (`uv`):

```text
hermes/
├── apps/
│   ├── hermes/            # React 19 + React Router v8 SSR frontend
│   ├── hermes-api/        # Stateless FastAPI REST API service
│   ├── hermes-worker/     # Batch CLI ingestion and lifecycle worker
│   └── hermes-e2e/        # Playwright end-to-end test suite
├── libs/
│   ├── map/               # Mapbox GL JS WebGL map engine & Zustand store
│   └── shared/
│       ├── hermes-ai/     # LiteLLM extraction, embeddings & Nominatim geocoding
│       ├── hermes-db/     # SQLAlchemy 2.0 models, PostGIS & pgvector HNSW
│       ├── ui-components/ # Shared HUD components (Tailwind CSS v4 & Base UI)
│       └── util-types/    # Hand-mirrored TypeScript API contracts
└── docs/
    └── architecture.md    # In-depth architectural specifications & diagrams
```

### Component Breakdown

| Project | Type | Description |
| :--- | :--- | :--- |
| [`@hermes/hermes`](apps/hermes/README.md) | Web Client | SSR React 19 application with Clerk authentication and Mapbox WebGL viewport. |
| [`hermes-api`](apps/hermes-api/README.md) | REST API | FastAPI application serving spatial bounding box queries and timeline synthesis. |
| [`hermes-worker`](apps/hermes-worker/README.md) | Batch CLI | Ephemeral run-and-die container orchestrating feed sync and lifecycle decay. |
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
   Ensure your `.env` contains database settings, Clerk authentication keys, and your Mapbox public token. For LLM capabilities, configure `LLM_API` and `EMBED_API` in `apps/hermes-api/.env.local`.

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

7. **(Optional) Run a worker ingestion sync**:
   ```bash
   # Executes a one-shot fetch, deduplication, and geocoding pass
   npx nx run hermes-worker:run-sync
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
  - [AI & Geocoding Services](libs/shared/hermes-ai/README.md)
  - [Database Schemas & Models](libs/shared/hermes-db/README.md)
  - [UI Component Library](libs/shared/ui-components/README.md)
  - [TypeScript Contracts](libs/shared/util-types/README.md)

---

## License

This project is licensed under the [MIT License](LICENSE).
