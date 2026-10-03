# Hermes Worker — AI Agent Context

This document provides worker-specific architectural context for the `hermes-worker` standalone CLI application. It is scoped to `apps/hermes-worker/` and supplements the root `AGENTS.md`.

---

## 1. Application Role & Architecture

`hermes-worker` is the **ephemeral data ingestion and event lifecycle processing worker** of Project Hermes. It is a pure Python application built with **feedparser**, **LiteLLM**, **httpx**, and **hermes-db**, managed with `uv` and integrated into Nx via `@nxlv/python`.

### 12-Factor Ephemeral Process Model
Adhering strictly to 12-factor architecture:
- **Stateless & Disposable**: The worker does not run long-lived in-process schedulers (e.g. APScheduler). Instead, it provides deterministic CLI commands designed to be triggered externally on a schedule (e.g. via container orchestrator cron, systemd timers, or background task runners).
- **Decoupled from Web API**: Keeping ingestion and score decay in a separate application prevents event loop starvation, memory leaks, and task duplication across horizontally scaled `hermes-api` replicas.

---

## 2. Ingestion Pipeline Flow

```text
┌─────────────────┐   ┌─────────────────┐   ┌────────────────┐   ┌──────────────┐   ┌─────────────┐   ┌───────────┐
│ hermes-worker   │──▶│ feedparser      │──▶│ LiteLLM Embed  │──▶│ pgvector     │──▶│ LiteLLM Ext │──▶│ Nominatim │──▶ PostGIS
│ (run-sync)      │   │ (httpx Sem(5))  │   │ (nemotron 2048)│   │ (HNSW < 0.25)│   │ (Mistral/NIM│   │ (Geocode) │    (via hermes-db)
└─────────────────┘   └─────────────────┘   └────────────────┘   └──────────────┘   └─────────────┘   └───────────┘
```

### Stage Details

1. **Source Discovery (`sync.py`)**: Queries `hermes-db` for active RSS sources where `last_fetched_at + fetch_interval_minutes <= NOW()` (or all sources when `--force` is passed).
2. **Parallel Fetching (`rss.py`)**: Uses `asyncio.Semaphore(5)` and `httpx.AsyncClient` to fetch RSS feeds concurrently. Content is sanitized and truncated to 500 words (`MAX_CONTENT_WORDS`). URL deduplication against the `articles` table immediately drops previously ingested stories.
3. **Semantic Filtering (`ai.py`)**: Batched article texts are converted into 2048-dimensional vector embeddings (`nvidia_nim/nvidia/nemotron-3-embed-1b`) guarded by `EMBED_RPM_LIMIT`. Candidate duplicates are retrieved from PostGIS using cosine distance against active events (`Event.embedding.cosine_distance(emb) < 0.25`, limit 5 per article).
4. **AI Batch Extraction (`ai.py`)**:
   - Sends article inputs and candidate events to the LiteLLM router in **batches of 10** (`ARTICLE_BATCH_SIZE`) guarded by `RPM_LIMIT`.
   - **Primary Model**: `mistral/ministral-8b-latest`.
   - **Fallback Model**: `nvidia_nim/mistralai/mistral-nemotron`.
   - The model determines whether to merge the article into an existing candidate event or create a new event.
   - Extracted attributes: headline, summary, category, category color (from `PREDEFINED_CATEGORIES`), and location name.
5. **Geocoding Shield (`geocoding.py` + PostGIS Cache)**:
   - Extracted location strings are checked against `geocode_cache` by normalized key (`location_name.strip().lower()`).
   - Cache misses call Nominatim under an `asyncio.Lock()` with a mandatory 1.0-second delay to comply with OpenStreetMap rate limits.
   - Results (including negative `NULL` results) are permanently cached to prevent redundant lookups.
6. **Persistence & Consensus Scoring (`sync.py` via `EventService`)**:
   - **Matched Event**: Adds `Article`, increments `article_count`, adds source credibility weight to `trending_score`, updates `last_updated_at`, and reactivates event if `STALE`.
   - **New Event**: Inserts `Event` with SRID 4326 `POINT` geometry, initial credibility score, and embedding vector.

---

## 3. Event Lifecycle & Time Decay (`lifecycle.py`)

Maintains event relevance over time:
- **Hourly Score Decay**: Multiplies `trending_score` by `0.90` (-10%) across all `ACTIVE` events per run.
- **Status Transitions**:
  - `ACTIVE` &rarr; `STALE` after 24 hours (`EVENT_STALE_HOURS`) without new articles.
  - `STALE` &rarr; `ARCHIVED` after 48 hours (`EVENT_ARCHIVE_HOURS`) without new articles.

---

## 4. CLI Commands & Usage

All worker jobs are executed via `hermes_worker.cli`:

```bash
# Execute RSS ingestion for due sources (or all with --force)
uv run python -m hermes_worker.cli run-sync [--force]

# Execute score decay and status transitions
uv run python -m hermes_worker.cli run-lifecycle

# Execute lifecycle transitions followed by due source sync
uv run python -m hermes_worker.cli run-all [--force]
```

Via Nx from workspace root:
```bash
npx nx run hermes-worker:run --args="run-all --force"
npx nx test hermes-worker
npx nx lint hermes-worker
```

---

## 5. Project Structure

```text
apps/hermes-worker/
├── Dockerfile                   # Standalone container build
├── project.json                 # Nx targets (build, test, lint, run)
├── pyproject.toml               # Dependencies (feedparser, litellm, httpx, hermes-db)
├── src/hermes_worker/
│   ├── __main__.py              # Package executable entrypoint
│   ├── cli.py                   # Argument parser and command router
│   ├── core/
│   │   ├── config.py            # Pydantic settings (multi-env cascade)
│   │   ├── constants.py         # Predefined category colors and defaults
│   │   ├── logger.py            # Parameterized structured logging
│   │   └── rate_limiter.py      # Token-bucket rate limiter for LLM APIs
│   └── services/
│       ├── ai.py                # LiteLLM embeddings & batch extraction
│       ├── geocoding.py         # Nominatim client with rate-limiting lock
│       ├── lifecycle.py         # Lifecycle transitions & score decay runner
│       ├── rss.py               # Feedparser + httpx parallel fetcher
│       └── sync.py              # Orchestrates the end-to-end ingestion pipeline
└── tests/                       # Unit and integration test suite
```
