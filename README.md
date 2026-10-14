# Hermes: Real-Time Geospatial Intelligence Engine

<div align="center">

```text
  ██╗  ██╗███████╗██████╗ ███╗   ███╗███████╗███████╗
  ██║  ██║██╔════╝██╔══██╗████╗ ████║██╔════╝██╔════╝
  ███████║█████╗  ██████╔╝██╔████╔██║█████╗  ███████╗
  ██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══╝  ╚════██║
  ██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗███████║
  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝
```

**Global Situational Awareness & Autonomous Geospatial News Aggregator**

[![Nx Workspace](https://img.shields.io/badge/Nx-Monorepo_23.2-143055?style=flat&logo=nx&logoColor=white)](https://nx.dev)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![React 19](https://img.shields.io/badge/React-19.2-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![React Router 8](https://img.shields.io/badge/React_Router-8.3-CA4245?style=flat&logo=react-router&logoColor=white)](https://reactrouter.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?style=flat&logo=postgresql&logoColor=white)](https://postgis.net)
[![pgvector](<https://img.shields.io/badge/pgvector-halfvec(2048)-blue?style=flat>)](https://github.com/pgvector/pgvector)
[![Tailwind CSS 4](https://img.shields.io/badge/Tailwind-4.3-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Mapbox GL JS](https://img.shields.io/badge/Mapbox_GL-v3.29-4264FB?style=flat&logo=mapbox&logoColor=white)](https://docs.mapbox.com/mapbox-gl-js/)
[![AWS Fargate](https://img.shields.io/badge/AWS-ECS_Fargate-FF9900?style=flat&logo=amazonaws&logoColor=white)](https://aws.amazon.com/fargate/)

</div>

---

## 1. Product Vision & Motivation ("The Why")

Modern digital news distribution suffers from a structural crisis: **news fatigue**. Traditional news portals and social feeds bombard users with endless, vertically scrolling rivers of text. This paradigm generates three systemic failure modes:

1. **Redundancy & Noise**: Hundreds of outlets report the identical underlying event, forcing readers to parse duplicate prose to understand what happened.
2. **Loss of Geographic Context**: Incidents are presented as abstract headlines detached from the spatial reality of borders, trade chokepoints, and regional topography.
3. **Sensationalist Recency Bias**: Feeds prioritize click-through rate over editorial consensus, conflating minor controversies with critical geopolitical shifts.

### The Spatial Intelligence Paradigm

**Project Hermes fundamentally transforms how humans observe global current events.** Instead of _reading_ articles in isolation, users _observe_ the world unfolding in real time on an interactive, tactical WebGL command map:

- **Spatially Grounded**: Incidents are anchored to verified geographical coordinates (`POINT`, SRID 4326) on the globe.
- **Editorial Consensus Engine**: Individual stories compound in significance only when it's corroborated by multiple independent global outlets across tiered credibility ranks.
- **Organic Time Decay**: Trending scores diminish organically (-10% compound decay per hour), allowing fast-breaking events to seize immediate attention while stale stories naturally fade into archives over 24–48 hours.
- **Historical Causality (Timeline Engine)**: Analysts can click any active incident to generate an on-demand historical lineage, tracing causal antecedents and Wikipedia milestones directly to today's breaking news.

---

## 2. High-Level System Architecture

Hermes is organized as an **Nx polyglot monorepo** coupling high-throughput asynchronous Python microservices with a responsive React 19 WebGL frontend client, underpinned by a PostGIS spatial and vector database.

```mermaid
flowchart TD
    subgraph External["External Services & APIs"]
        RSS["Global RSS Feeds
(BBC, NYT, Reuters, Al Jazeera)"]
        OSM["OpenStreetMap Nominatim
(Geocoding Engine)"]
        Wiki["MediaWiki REST API
(Historical Archives)"]
        LLM["LiteLLM Inference
(Mistral / NVIDIA NIM)"]
    end

    subgraph Orchestration["Cloud Orchestration (AWS)"]
        EventBridge["Amazon EventBridge
cron(0 0,8,16 * * ? *)"]
    end

    subgraph Worker["Ingestion Engine (apps/hermes-worker)"]
        Fargate["AWS ECS Fargate Task (0.25 vCPU, 512 MiB)
hermes-worker run-all"]
        RSSFetcher["Async Feedparser + HTTPX Fetcher"]
        Embedder["Nemotron Vector Embedder (2048-dim)"]
        Deduplicator["Semantic Deduplicator (HNSW Cosine)"]
        AIExtractor["Batch AI Extraction (LiteLLM)"]
        GeoShield["Geocoding Shield (Token Bucket 1.0s Lock)"]
        LifecycleEngine["Time Decay Engine (-10%/hr & Archival)"]
    end

    subgraph Database["Spatial & Vector Database (libs/shared/hermes-db)"]
        PostGIS[("Neon Serverless PostgreSQL 16
- Point Geometry (SRID 4326) + GIST Index
- pgvector halfvec(2048) + HNSW Index
- Permanent Geocode Cache Table
- Historical Timeline JSONB Nodes & Edges")]
    end

    subgraph API["Backend REST API (apps/hermes-api)"]
        FastAPI["FastAPI Stateless REST App"]
        BBoxQuery["Dynamic Viewport Bounding Box (ST_Within)"]
        TimelineSvc["Historical Causality Synthesizer"]
    end

    subgraph Frontend["Mission Control HUD (apps/hermes & libs/map)"]
        ZustandStore["Zustand Map Telemetry Store (Single Truth)"]
        TanStackQuery["TanStack Query v5 (Spatial BBox Sync)"]
        MapboxEngine["Mapbox GL JS v3 (Native WebGL Clustering)"]
        TacticalHUD["Mission Control HUD (Zero Border Radius)"]
        TimelineDrawer["Timeline Investigation Drawer (TlPanel)"]
    end

    EventBridge -->|Triggers ecs:RunTask (3x daily)| Fargate
    Fargate --> LifecycleEngine
    LifecycleEngine --> PostGIS
    Fargate --> RSSFetcher
    RSSFetcher <--> RSS
    RSSFetcher --> Embedder
    Embedder <--> LLM
    Embedder --> Deduplicator
    Deduplicator <-->|HNSW Cosine Search < 0.25| PostGIS
    Deduplicator --> AIExtractor
    AIExtractor <--> LLM
    AIExtractor --> GeoShield
    GeoShield <--> OSM
    GeoShield <-->|Cache Check & Store| PostGIS
    GeoShield -->|Commit Events & Articles| PostGIS

    API <-->|SQLAlchemy 2.0 AsyncPool| PostGIS
    API <--> Wiki
    API <--> LLM

    ZustandStore <--> TanStackQuery
    TanStackQuery <-->|REST: /api/v1/events/bbox| API
    TimelineDrawer <-->|REST: /api/v1/events/tl| API
    ZustandStore --> MapboxEngine
    MapboxEngine --> TacticalHUD
```

---

## 3. Core Architectural Decisions & Tradeoffs ("The Why")

Every structural choice in Hermes was made to solve specific engineering constraints around cost, throughput, memory, and accuracy:

### A. Ephemeral Serverless Worker vs. Long-Running Daemons

- **The Decision**: `hermes-worker` runs as a one-shot batch container (`hermes-worker run-all`) on **AWS ECS Fargate**, automatically invoked 3x daily by **Amazon EventBridge**. It executes lifecycle decay, fetches feeds, processes embeddings, commits to Neon, and terminates cleanly (`exit code 0`).
- **The Why & Tradeoffs**: Traditional architectures keep a VM or container running 24/7 with `time.sleep(28800)` or a `celery-beat` worker. That wastes money for 23.8 hours of idle CPU every day and creates memory leak risks in long-running Python processes parsing untrusted XML feeds. Fargate serverless execution costs ~$0.0003 per run (under **$0.05/month total**), with guaranteed clean memory state on every invocation.

### B. 16-Bit Half-Precision Vectors (`halfvec(2048)`) with HNSW

- **The Decision**: Vector embeddings generated by `nemotron-3-embed-1b` (2048 dimensions) are stored using `pgvector`'s `halfvec` (16-bit half precision) indexed with Hierarchical Navigable Small World (`halfvec_cosine_ops`).
- **The Why & Tradeoffs**:
  - Standard 32-bit float vectors require **8,192 bytes per row** for the embedding column alone.
  - Storing at 16-bit precision cuts this by 50% to **4,096 bytes per row**, halving RAM footprint and I/O overhead.
  - HNSW graph construction requires the index to fit in memory for fast traversals. `halfvec` allows Neon Serverless PostgreSQL to keep 10,000+ vector nodes cached in memory, ensuring duplicate detection lookups (`cosine distance < 0.25`) execute in under 15ms.

### C. Zero-Hallucination Geocoding Shield

- **The Decision**: Large Language Models are strictly prohibited from generating latitude and longitude coordinates. Instead, the AI extraction pipeline only extracts verified geographic location _names_ (e.g., `"Geneva, Switzerland"`). These names are resolved via OpenStreetMap's Nominatim service, shielded by a token-bucket rate limiter enforcing a strict 1-second delay, backed by a persistent `geocode_cache` database table.
- **The Why & Tradeoffs**: Generative models frequently hallucinate geographic coordinates (often placing land events in the middle of oceans). Grounded Nominatim resolution guarantees pinpoint map placement. The local database cache prevents duplicate external requests, drastically minimizing Nominatim rate usage.

### D. On-Demand Historical Causality Engine

- **The Decision**: Historical causal timelines are generated on-demand (`/api/v1/events/tl`) rather than precomputed during ingestion.
- **The Why & Tradeoffs**: Only a fraction of users inspect an event's historical lineage. Pre-synthesizing causal graphs across 300+ daily events would exhaust LLM token budgets and create unnecessary database bloat. On-demand synthesis queries the MediaWiki REST API for related historical pages, extracts causal node/edge graphs, grounds historical coordinates, and stitches today's breaking incident as the terminal node.

### E. Single Page Application Mode (`ssr: false`) with WebGL Engine

- **The Decision**: React Router 8 is explicitly configured in SPA mode (`ssr: false`). Mapbox GL JS renders pins and clusters directly on a 2D Mercator WebGL canvas.
- **The Why & Tradeoffs**: Server-Side Rendering (SSR) requires hydration of the DOM on the server, but WebGL requires active `HTMLCanvasElement` and `window` contexts that cannot be server-rendered. By operating as a pure SPA client, Zustand manages map camera telemetry as the single source of truth, and TanStack Query debounces bounding-box queries (`ST_Within`) as the user pans or zooms.

### F. Strict Nx 80/20 Apps-and-Libs Partitioning

- **The Decision**: All business logic, UI components, database models, and AI pipelines reside in shared libraries (`libs/`). Applications (`apps/`) are thin deployment configuration shells.
- **The Why & Tradeoffs**: Both `hermes-api` and `hermes-worker` need identical database models and AI pipelines. By placing them in `libs/shared/hermes-db` and `libs/shared/hermes-ai`, migrations and extraction logic are maintained in exactly one place with zero circular dependencies, enforced by ESLint module boundary rules.

---

## 4. Workspace Anatomy

Hermes is organized as an **Nx Monorepo** (TypeScript / React 19 + Python 3.14+ uv workspace):

```text
hermes/
├── apps/
│   ├── hermes/                  # React 19 + React Router 8 frontend shell (Vite, Tailwind CSS 4)
│   ├── hermes-api/              # Python FastAPI stateless REST API & timeline synthesizer
│   ├── hermes-worker/           # Python CLI worker for autonomous ingestion (AWS ECS Fargate)
│   └── hermes-e2e/              # Playwright browser end-to-end test suite
├── libs/
│   ├── map/                     # Core Mapbox GL JS WebGL canvas, clustering & timeline drawer
│   └── shared/
│       ├── hermes-ai/           # LiteLLM client, embeddings, extraction schemas & geocoding shield
│       ├── hermes-db/           # PostGIS models, alembic migrations, connection pool & DB services
│       ├── ui-components/       # Tactical Mission Control HUD widgets (BootSequence, LiveClock)
│       ├── util-types/          # Shared TypeScript API response and event interfaces
│       └── utils/               # Cross-cutting TypeScript helper utilities
├── .github/workflows/
│   ├── ci.yml                   # Workspace CI: Linting, typechecking, pytest & vitest across all 10 projects
│   └── cd-worker.yml            # Workspace CD: Builds production Docker image & pushes to Amazon ECR
├── docker-compose.yml           # Local development PostGIS 16 + pgvector container
├── package.json                 # Node 22 workspace dependencies & scripts
├── pyproject.toml               # Python 3.14+ uv workspace configuration & ruff settings
└── nx.json                      # Nx Crystal project graph & target configurations
```

### Monorepo Project Catalog

| Project Name                | Path                         | Type                | Key Technologies                                                                     |
| :-------------------------- | :--------------------------- | :------------------ | :----------------------------------------------------------------------------------- |
| **`@hermes/hermes`**        | `apps/hermes/`               | Frontend Shell      | React 19, React Router 8 (SPA), Vite, Mapbox GL JS v3, Zustand 5, Tailwind CSS 4     |
| **`hermes-api`**            | `apps/hermes-api/`           | Backend REST API    | Python 3.14+, FastAPI, SQLAlchemy 2.0 Async, PostGIS, pgvector, LiteLLM, uv          |
| **`hermes-worker`**         | `apps/hermes-worker/`        | Ingestion Worker    | Python 3.14+, feedparser, LiteLLM, PostGIS, pgvector, httpx, uv, Docker, AWS Fargate |
| **`@hermes/hermes-e2e`**    | `apps/hermes-e2e/`           | E2E Testing         | Playwright, TypeScript                                                               |
| **`@hermes/map`**           | `libs/map/`                  | Spatial UI Library  | Mapbox GL JS, Zustand store, TanStack Query hooks, `MapView`, `TlPanel`              |
| **`hermes-ai`**             | `libs/shared/hermes-ai/`     | AI & Geocoding Lib  | Python 3.14+, LiteLLM, Pydantic, httpx, Nominatim rate limiter, uv                   |
| **`hermes-db`**             | `libs/shared/hermes-db/`     | Database Models Lib | Python 3.14+, SQLAlchemy 2.0 Async, PostGIS, pgvector (`halfvec`), Alembic, uv       |
| **`@hermes/ui-components`** | `libs/shared/ui-components/` | Tactical HUD Lib    | React 19, Tailwind CSS 4, `BootSequence`, `LiveClock`, HUD overlays                  |
| **`@hermes/util-types`**    | `libs/shared/util-types/`    | Contract Lib        | TypeScript shared API interfaces (`MapEventResponse`, `TlResponse`)                  |
| **`@hermes/utils`**         | `libs/shared/utils/`         | Utility Lib         | Cross-cutting helper functions                                                       |

---

## 5. Domain Mechanics & Algorithmic Scoring

### A. Algorithmic Source Consensus

An incident's `trending_score` reflects multi-source verification. Sources are assigned strict credibility tiers:

| Credibility Tier | Weight Increment | Source Outlets (Examples)                                            |
| :--------------- | :--------------- | :------------------------------------------------------------------- |
| **`TIER_1`**     | **+3.0**         | Reuters, BBC News, Associated Press, Financial Times                 |
| **`TIER_2`**     | **+2.0**         | The New York Times, The Guardian, Al Jazeera, Deutsche Welle         |
| **`TIER_3`**     | **+1.0**         | Regional publications, specialized trade publications, wire services |
| **`TIER_4`**     | **+0.5**         | Blogs, syndicated aggregators, community-driven reports              |

When a incoming article matches an existing event within cosine vector distance `< 0.25`:
$$\text{Score}_{\text{new}} = \text{Score}_{\text{current}} + \text{Weight}(\text{Tier})$$

### B. Organic Time Decay Formula

To ensure fast-breaking news commands the map while older stories gracefully archive:

- Every hour, active events experience a compound **-10% decay**:
  $$\text{Score}_{t+1} = \text{Score}_{t} \times 0.90$$
- **Lifecycle State Transitions**:
  - **Active $\rightarrow$ Stale**: Events with no new corroborating articles for $> 24\text{ hours}$ transition to `STALE` status.
  - **Stale $\rightarrow$ Archived**: Events older than $> 48\text{ hours}$ transition to `ARCHIVED` status and drop off the live map viewport.

---

## 6. Local Development & Setup

### Prerequisites

- **Docker & Docker Compose** (for local PostGIS 16 + pgvector)
- **Node.js v22 LTS & npm**
- **Python 3.14+** (enforced in `pyproject.toml`)
- **`uv`** fast Python package and project manager ([astral.sh/uv](https://docs.astral.sh/uv/))
- **Mapbox Public Access Token** (from [mapbox.com](https://account.mapbox.com/))

---

### Step 1: Environment Configuration

Create a root `.env` file at the workspace root:

```ini
# Environment
ENV=development

# Network Ports
API_PORT=8000
FRONTEND_PORT=4200

# Local PostGIS Database Credentials
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hermes
DB_USER=postgres
DB_PASSWORD=secret

# Mapbox Access Token
VITE_MAPBOX_TOKEN=pk.your_mapbox_token_here
VITE_BASE_URL=http://localhost:8000
VITE_API_VER=v1
```

Create `.env.local` inside `apps/hermes-api/` and `apps/hermes-worker/`:

```ini
# AI Inference Credentials (LiteLLM)
LLM_API=your_mistral_or_nim_api_key
LLM_MODEL=mistral/ministral-8b-latest

# Vector Embedding Credentials (NVIDIA NIM)
EMBED_API=your_nvidia_nim_api_key
EMBED_MODEL=nvidia_nim/nvidia/nemotron-3-embed-1b
```

---

### Step 2: Installation & Launch Commands

All commands are executed from the **workspace root**:

```bash
# 1. Install Node.js dependencies
npm ci

# 2. Synchronize Python virtual environment and dependencies via uv
npx nx run hermes-api:sync
npx nx run hermes-worker:sync

# 3. Start local PostGIS spatial database container
docker compose up -d hermes-db

# 4. Run Alembic database migrations to head
npx nx run hermes-api:migrate

# 5. Start the backend REST API (FastAPI with hot reload on port 8000)
npx nx serve hermes-api

# 6. Start the frontend development server (Vite on port 4200)
npx nx dev @hermes/hermes

# 7. Execute the worker ingestion pipeline
# Option A: One-shot batch execution (processes RSS feeds and exits cleanly)
npx nx run hermes-worker:run-all

# Option B: Continuous local polling loop
npx nx run hermes-worker:run
```

---

## 7. Testing & Quality Assurance

Hermes maintains 100% test pass rates across all 10 monorepo packages.

```bash
# Run linting across TypeScript (ESLint) and Python (Ruff)
npm run lint

# Run all unit test suites (Vitest for frontend/libs, Pytest for backend/worker/db/ai)
npm test

# Run Python linting and testing specifically
npm run lint:py
npm run test:py

# Run End-to-End browser tests (Playwright)
npx nx e2e @hermes/hermes-e2e
```

---

## 8. Production Cloud Architecture

In production, Hermes is deployed as a resilient, cost-optimized multi-cloud system:

- **Spatial & Vector Database**: **Neon Serverless PostgreSQL 16** with native `postgis` and `pgvector` extensions enabled.
- **Autonomous Worker**: **AWS ECS Fargate** serverless container (`0.25 vCPU`, `512 MiB`) running in region `ap-southeast-2` (Sydney), automatically orchestrated 3 times daily by **Amazon EventBridge** (`cron(0 0,8,16 * * ? *)`).
- **CI/CD Pipeline**: GitHub Actions runs full quality gating (`ci.yml`) on every pull request and push to `master` and `dev`. Upon a green CI build, `cd-worker.yml` builds the multi-stage production Docker image and pushes tags to a private **Amazon ECR** repository.

---

## 9. Comprehensive Documentation Index

Deep architectural dives, API schemas, and library guides are available across the workspace:

| Document                                                                         | Scope & Contents                                                                                       |
| :------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| [**`AGENTS.md`**](AGENTS.md)                                                     | **System Constitution**: AI Agent persona, global architectural rules, and monorepo boundaries.        |
| [**`apps/hermes/README.md`**](apps/hermes/README.md)                             | **Frontend App Guide**: Route layout, Vite configuration, and client-side telemetry store.             |
| [**`apps/hermes/AGENTS.md`**](apps/hermes/AGENTS.md)                             | **Frontend AI Context**: SPA mode rationale, unidirectional data flow, and WebGL rendering boundaries. |
| [**`apps/hermes-api/README.md`**](apps/hermes-api/README.md)                     | **REST API Guide**: Endpoints (`/bbox`, `/tl`), lifespan initialization, and exception handling.       |
| [**`apps/hermes-api/AGENTS.md`**](apps/hermes-api/AGENTS.md)                     | **API AI Context**: Stateless 12-factor boundaries, timeline orchestration, and CORS handling.         |
| [**`apps/hermes-worker/README.md`**](apps/hermes-worker/README.md)               | **Worker App Guide**: RSS ingestion stages, AWS Fargate/EventBridge specifications, and CLI commands.  |
| [**`apps/hermes-worker/AGENTS.md`**](apps/hermes-worker/AGENTS.md)               | **Worker AI Context**: Ephemeral run-and-die constraints, batching limits, and geocoding shields.      |
| [**`libs/map/README.md`**](libs/map/README.md)                                   | **Map Library Guide**: WebGL layers, clustering parameters, camera hops, and `TlPanel` drawer.         |
| [**`libs/shared/hermes-ai/README.md`**](libs/shared/hermes-ai/README.md)         | **AI & Geocoding Guide**: LiteLLM polymorphic schemas, token-bucket rate limiter, and Nominatim cache. |
| [**`libs/shared/hermes-db/README.md`**](libs/shared/hermes-db/README.md)         | **Database Models Guide**: PostGIS geometry, `halfvec(2048)` HNSW schema, and Alembic migrations.      |
| [**`libs/shared/ui-components/README.md`**](libs/shared/ui-components/README.md) | **Tactical HUD Guide**: Monospace typography, `BootSequence`, `LiveClock`, and HUD widgets.            |
| [**`libs/shared/util-types/README.md`**](libs/shared/util-types/README.md)       | **Shared Types Guide**: TypeScript response contracts between API schemas and frontend consumers.      |
