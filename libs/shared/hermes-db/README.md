# `hermes-db`

Shared asynchronous persistence library for Hermes. It defines the SQLAlchemy 2.0 models, PostGIS geometry, pgvector HNSW indexes, domain services, and Alembic migrations used by both `hermes-api` and `hermes-worker`.

## Responsibilities

- Own the database schema as the single source of truth across 11 ORM models: `Source`, `Article`, `ArticleLabel`, `ArticleFamily`, `Event`, `EventMember`, `EventRelationship`, `ClusterDecision`, `Thread`, `EventTl`, and `GeocodeCache`.
- Provide async services for ingestion queues, article analysis, syndication families, event clustering, verification, deterministic importance scoring, story threads, non-destructive merges, pairwise event relationships, hybrid search, timelines, maintenance/retention, and geocode caching.
- Initialize the engine and session factory from a URL supplied by the consumer.
- Apply every schema change through Alembic.

The library never reads `.env` files or `os.environ`. Consumers validate configuration and call `init_db()` at startup. Alembic's `migrations/env.py` is the only standalone resolver.

## Models

| Model | Table | Notes |
| :--- | :--- | :--- |
| `Source` | `sources` | Publisher/feed configuration, provider/fetch policy, health tracking, soft-disabled via `is_active`. |
| `Article` | `articles` | Ingestion ledger & `FOR UPDATE SKIP LOCKED` queue, canonical URL identity, SimHash digests, deferred `halfvec(2048)` embedding. |
| `ArticleLabel` | `article_labels` | Structured factual extraction per article (`is_event`, `certainty`, `severity`, `specificity`, `consequence`, `entities`, `locations`). |
| `ArticleFamily` | `article_families` | Wire/syndication copy groupings anchored to a representative article to prevent duplicate corroboration. |
| `Event` | `events` | Denormalized incident aggregate with `geometry(POINT, 4326)`, `halfvec(2048)` embedding, `importance_score`, `selection_tier`, `actors` JSONB, and merge redirects (`merged_into_id`). |
| `EventMember` | `event_members` | Historical membership join table enforcing at most one current event per article (`is_current`). |
| `EventRelationship` | `event_relationships` | Directed typed edges (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`) between distinct events with unordered-pair uniqueness. |
| `ClusterDecision` | `cluster_decisions` | Pairwise LLM adjudication cache keyed by deterministic `pair_hash` across clustering, merges, threads, and relationships. |
| `Thread` | `threads` | Persistent topic/developing story groupings with `halfvec(2048)` centroids, `importance`, and `ACTIVE`/`DORMANT`/`ENDED` status. |
| `EventTl` | `event_timelines` | One-to-one historical causality DAG stored as JSONB `nodes`/`edges` with `event_version` staleness tracking. |
| `GeocodeCache` | `geocode_cache` | Normalized location-name cache; `NULL` coordinates act as a negative cache. |

All `datetime` columns map to `TIMESTAMPTZ`, and application code writes aware UTC. `Event.articles`, `Event.memberships`, and `EventRelationship` relations use `lazy="raise"`; read paths must eager-load explicitly.

## Services

| Module / Class | Focus |
| :--- | :--- |
| `ArticleService` (`article.py`) | URL existence checks, ledger queries, and idempotent article insertion. |
| `ArticleAnalysisService` (`article_analysis.py`) | Analysis result persistence, embeddings, and rejection/labeling state updates. |
| `ArticleFamilyService` (`article_family.py`) | Syndication family creation, candidate lookup, and attachment. |
| `ArticleLabelService` (`article_label.py`) | `ArticleLabel` creation and uniqueness lookup per prompt version. |
| `ClusterDecisionService` (`cluster_decision.py`) | `pair_hash` lookup and persistence for cached LLM adjudications. |
| `EventService` (`event.py`) | Read-side queries (map bbox, FTS, hybrid search, redirect-aware event detail, relationship counts). |
| `EventAssignmentService` (`event_assignment.py`) | ANN + country-blocked candidate loading for article clustering. |
| `EventLifecycleService` (`event_lifecycle.py`) | Deterministic `ACTIVE -> STALE -> ARCHIVED` transitions and stale embedding pruning. |
| `EventMembershipService` (`event_membership.py`) | Member attachment/detachment, origin/count aggregation, centroid updates, and `member_hash` tracking. |
| `EventMergeService` (`event_merge.py`) | Non-destructive duplicate event merging, relationship repointing, timeline invalidation, and redirect chain resolution. |
| `EventRelationshipService` (`event_relationship.py`) | Relationship candidate recall, upsert, unordered-pair cache checks, bbox edge projection, and event detail links. |
| `EventScoringService` (`event_scoring.py`) | Deterministic `score-v2` `importance_score` formula, exponential decay, single-source cap, and hysteresis `SelectionTier` classification. |
| `GeocodeCacheService` (`geocode.py`) | First-write-wins geocode cache with negative-cache semantics. |
| `MaintenanceService` (`maintenance.py`) | Count reconciliation, consistency drift reporting, stale-claim requeuing helpers, and retention purges. |
| `SearchService` (`search.py`) | Hybrid lexical + semantic retrieval with RRF, scope filters, coverage classification, and context hydration for chat. |
| `SourceService` (`source.py`) | Due-source selection, fetch health tracking, and `sources.json` catalog sync. |
| `ThreadService` (`thread.py`) | Story thread CRUD, candidate scoring (`0.70` cosine + `0.30` entity Jaccard), importance recomputation, and `ACTIVE`/`DORMANT`/`ENDED` lifecycle. |
| `EventTlService` (`tl.py`) | Timeline creation, status transitions, generated-graph persistence, and deletion. |
| `verification.py` (`compute_verification`) | Independent origin-group derivation and `VerificationStatus` classification. |

## Session Lifecycle

```python
from hermes_db import close_db, get_db, init_db

await init_db("postgresql+asyncpg://user:pass@host/hermes")
# FastAPI: session = Depends(get_db)
await close_db()
```

`init_db()` creates an `AsyncEngine` with `pool_pre_ping=True` and `statement_cache_size=0` (required for PgBouncer transaction pooling), probes connectivity, and syncs the source catalog. `get_db()` yields an `AsyncSession` and rolls back on exceptions.

## Migrations

The chain is linear: 28 revisions from root `2ec3541646e8` to head `219faff153a6`. Recent revisions introduced typed cross-event relationships (`33ae8a869e4e`, creating `event_relationships`) and structured actor extraction (`219faff153a6`, adding `events.actors`).

```bash
npx nx run hermes-db:makemigrations -- -m "<message>"
npx nx run hermes-db:migrate
```

Never edit an applied revision or use `Base.metadata.create_all()`.

## Commands

```bash
npx nx lint hermes-db
npx nx test hermes-db
npx nx run hermes-db:format
```

## Related Docs

- [`AGENTS.md`](AGENTS.md) — invariants and tunables.
- [`docs/architecture.md`](docs/architecture.md) — schema, query design, migration chain, and ADRs.
