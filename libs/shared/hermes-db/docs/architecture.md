# Hermes DB — Architecture & Design Rationale

`libs/shared/hermes-db` is the asynchronous persistence foundation of Hermes. It is an internal **library**, not a service: consumer applications (`apps/hermes-api`, `apps/hermes-worker`, `apps/hermes`) own their process lifecycle and inject database connection parameters, while this package owns the schema, SQLAlchemy 2.0 ORM models, Alembic migrations, PostGIS spatial queries, pgvector embeddings, and persistence-facing domain services.

The design goal is strict encapsulation of all database concerns: consumer applications orchestrate pipelines and serve API requests without embedding SQL strings, PostGIS expressions, vector distance math, or schema knowledge.

> **Companion reading:**
> - [Workspace Instructions](file:///home/pavan/proj/hermes/hermes/AGENTS.md)
> - [Worker Architecture](file:///home/pavan/proj/hermes/hermes/apps/hermes-worker/docs/architecture.md)
> - [API Architecture](file:///home/pavan/proj/hermes/hermes/apps/hermes-api/docs/architecture.md)
> - [Database Guidelines](file:///home/pavan/proj/hermes/hermes/libs/shared/hermes-db/AGENTS.md)

---

## 1. Mission, Scope, and Architectural Boundaries

### 1.1 Core Responsibilities

- **Canonical Data Models**: Declare SQLAlchemy 2.0 models for sources, article ingestion ledgers, article labels, syndication families, events, event membership history, pairwise cluster decisions, persistent story threads, causality timelines, and geocoding cache.
- **Alembic Schema Authority**: Own every database migration revision and execution environment.
- **Asynchronous Persistence Services**: Provide domain services for article claiming and lifecycle queues, syndication family grouping, event creation, membership aggregation, deterministic scoring, thread clustering, non-destructive event merging, and scheduled retention sweeps.
- **Spatial & Vector Primitives**: Manage PostGIS geometry points (SRID 4326 WGS 84), spatial bounding-box filters, coordinate projection via SQL `ST_X` / `ST_Y`, and pgvector `HALFVEC(2048)` HNSW indexing with cosine distance.
- **Lexical & Semantic Search**: Provide full-text search indexes (`tsvector`), weighted document rankers, and hybrid vector retrieval.

### 1.2 Explicit Non-Responsibilities

- **No Network I/O or Feeds**: Never perform HTTP calls, RSS parsing, GDELT fetching, or HTML scraping.
- **No LLM Prompts or Inference**: Never construct prompts or call AI providers. LLM generation and embedding synthesis are orchestrated by `hermes-worker` via `libs/shared/hermes-ai`.
- **No Direct Geocoding Calls**: The library stores and queries `geocode_cache`; the rate-limited Nominatim geocoder lives in `libs/shared/hermes-ai`.
- **No Application Lifecycles**: Never create standalone daemons, FastAPI routers, or CLI schedulers.
- **No Outward Dependencies**: Dependency flow is strictly unidirectional. `hermes-db` never imports from `apps/*` or `libs/shared/hermes-ai`.

### 1.3 Consumers & Usage Patterns

| Consumer | Invocation Mechanism | Primary Services & Models |
| :--- | :--- | :--- |
| `apps/hermes-api` | FastAPI lifespan `init_db` / `close_db`, `Depends(get_db)` | `EventService` (map bbox, FTS, hybrid search), `EventTlService`, `ThreadService`, `GeocodeCacheService` |
| `apps/hermes-worker` | CLI batch jobs via `db_lifespan()` | `ArticleService`, `ArticleAnalysisService`, `ArticleFamilyService`, `EventAssignmentService`, `EventScoringService`, `EventMembershipService`, `EventMergeService`, `EventLifecycleService`, `ThreadService`, `MaintenanceService` |
| Alembic CLI | `npx nx run hermes-db:migrate` / `makemigrations` | `migrations/env.py`, `Base.metadata` |
| Unit Tests | Pure in-memory SQLite / mock session tests | Models, Enums, Math formulas, SQL expression compilation |

### 1.4 Architectural Invariants

1. **Unidirectional Dependency**: `hermes-db` never imports application code.
2. **Inversion of Control (IoC) for Configuration**: Domain code never inspects `os.environ` or `.env` files. Consumers load environment variables and pass validated connection strings to `init_db(db_url)`. Standalone Alembic CLI is the sole exception (`migrations/env.py`).
3. **Transaction Boundaries Belong to Callers**: Domain services (`EventScoringService`, `EventMergeService`, etc.) **never commit** transactions (`await session.commit()`). They flush state (`await session.flush()`) when generated IDs are required, leaving commit and rollback semantics to the orchestrating worker stage or API route.
4. **Statement Caching Disabled**: Every engine instance configures `connect_args={"statement_cache_size": 0}` to support transaction-mode connection poolers (e.g. PgBouncer on Neon Serverless).
5. **Direct SQL Coordinate Projection**: Longitude and latitude are projected via `ST_X` and `ST_Y` in SQL expressions rather than serializing/deserializing WKB geometry objects on the client.
6. **Alembic-Only Schema Evolution**: Schema mutations are executed strictly via Alembic revisions. Raw SQL DDL and `Base.metadata.create_all()` are strictly prohibited.
7. **Spatial Coordinate Standard**: All stored locations are `POINT` geometries in SRID 4326, ordered `(longitude, latitude)`.
8. **No Redundant Tables or Columns**: Defer to minimum justified schema. Embeddings live directly on `articles.embedding` and `events.embedding` as deferred `HALFVEC(2048)`.

---

## 2. Entity-Relationship Data Model

The following diagram illustrates the core entity relationships across ingestion, clustering, scoring, story threading, and causality:

```mermaid
erDiagram
    SOURCES ||--o{ ARTICLES : "publishes"
    ARTICLES ||--o| ARTICLE_LABELS : "labeled by"
    ARTICLES }o--o| ARTICLE_FAMILIES : "belongs to"
    ARTICLES ||--o{ EVENT_MEMBERS : "attaches to"
    EVENTS ||--o{ EVENT_MEMBERS : "contains"
    EVENTS }o--o| THREADS : "grouped under"
    EVENTS ||--o{ EVENT_TIMELINES : "causality timeline"
    EVENTS }o--o| EVENTS : "merged_into_id"
    ARTICLES }o--o| ARTICLES : "duplicate_of_id"

    SOURCES {
        uuid id PK
        string name
        string slug UK
        string url
        string feed_url
        string provider
        string fetch_policy
        string origin_group
        string credibility_tier
    }

    ARTICLES {
        uuid id PK
        uuid source_id FK
        uuid event_id FK
        uuid duplicate_of_id FK
        uuid family_id FK
        string url UK
        string canonical_url
        string canonical_url_hash
        string title
        string title_simhash
        string body_simhash
        string content_hash
        int word_count
        string body_source
        string ingest_status
        timestamp published_at
        timestamp ingested_at
        timestamp claimed_at
        string claimed_by
        int attempt_count
        string last_error
        string reject_stage
        string reject_reason
        halfvec_2048 embedding
        string embedding_model
        string embedding_input_hash
    }

    ARTICLE_LABELS {
        uuid id PK
        uuid article_id FK
        string prompt_version
        string model
        boolean is_event
        string article_type
        string category
        string event_form
        string certainty
        int severity
        int specificity
        int consequence
        float confidence
        string fact
        jsonb scale_facts
        jsonb entities
        jsonb locations
        string evidence_quote
        string reject_reason
        timestamp labeled_at
    }

    ARTICLE_FAMILIES {
        uuid id PK
        uuid representative_article_id FK
        string title_simhash
        string body_simhash
        string primary_origin_group
        int member_count
        timestamp created_at
        timestamp updated_at
    }

    EVENTS {
        uuid id PK
        uuid thread_id FK
        uuid merged_into_id FK
        string ai_headline
        string ai_summary
        string category
        string category_color
        string status
        string scope
        string impact_level
        string verification_status
        string selection_tier
        string selection_reason
        float importance_score
        string score_version
        jsonb score_breakdown
        geometry location
        string location_name
        string country_code
        int article_count
        int source_count
        int family_count
        int independent_origin_count
        string member_hash
        int version
        halfvec_2048 embedding
        string embedding_model
        timestamp event_time
        timestamp first_reported_at
        timestamp latest_published_at
        timestamp scored_at
        timestamp selected_at
    }

    EVENT_MEMBERS {
        uuid id PK
        uuid event_id FK
        uuid article_id FK
        boolean is_current
        string method
        float confidence
        jsonb score_breakdown
        timestamp assigned_at
        timestamp removed_at
    }

    CLUSTER_DECISIONS {
        string pair_hash PK
        string decision
        float confidence
        string model
        string prompt_version
        timestamp created_at
    }

    THREADS {
        uuid id PK
        string name
        string name_norm
        string kind
        string status
        string description
        jsonb entities
        jsonb keywords
        float importance
        int event_count
        halfvec_2048 embedding
        string embedding_model
        timestamp started_at
        timestamp last_event_at
        timestamp ended_at
    }

    EVENT_TIMELINES {
        uuid id PK
        uuid event_id FK
        string status
        int event_version
        jsonb key_events
        jsonb context
        timestamp generated_at
    }

    GEOCODE_CACHE {
        string query_hash PK
        string query
        string display_name
        geometry location
        string country_code
        float confidence
        timestamp cached_at
    }
```

---

## 3. Article Ingestion Ledger & Queue

The `articles` table serves as an immutable ingestion ledger, deduplication gate, and asynchronous work queue.

### 3.1 Ledger Identity & Deduplication

1. **URL Normalization & Hash**: Incoming links are normalized and fingerprinted via `canonical_url_hash = sha256(canonical_url)`. A partial unique index prevents redundant ledger rows:
   ```sql
   CREATE UNIQUE INDEX uq_articles_canonical_url_hash
   ON articles (canonical_url_hash)
   WHERE duplicate_of_id IS NULL;
   ```
2. **Idempotent Ingestion**: Raw articles are inserted using `ON CONFLICT (url) DO NOTHING`. Ingest never updates existing articles in place or revives superseded records.
3. **SimHash & Content Hashes**: Articles carry 64-bit SimHash hex digests for title (`title_simhash`) and transient body text (`body_simhash`), enabling fast Bitwise Hamming distance filtering during syndication grouping.
4. **Transient Bodies**: Fetched article bodies are never persisted. Only the extracted labels, entities, fingerprints, and a bounded `evidence_quote` (≤400 characters) are written to disk.

### 3.2 Claim Queue State Machine

The queue status is governed by `Article.ingest_status`:

```
NEW ──► ANALYZING ──► LABELED ──► CLUSTERED
            │              │
            ▼              ▼
          FAILED        REJECTED (with reject_stage and reject_reason)
```

- **Concurrency Control**: Stages claim batches via `ArticleQueue` using atomic PostgreSQL row locks:
  ```sql
  UPDATE articles
  SET ingest_status = 'ANALYZING',
      claimed_at = NOW(),
      claimed_by = :worker_id,
      attempt_count = attempt_count + 1
  WHERE id IN (
      SELECT id FROM articles
      WHERE ingest_status = 'NEW'
      ORDER BY published_at ASC NULLS LAST
      FOR UPDATE SKIP LOCKED
      LIMIT :batch_size
  )
  RETURNING *;
  ```
- **Abandonment & Requeuing**: `attempt_count` tracks retries. If an ephemeral worker dies, claims older than `ARTICLE_CLAIM_STALE_MINUTES` are cleared by `MaintenanceService.requeue_stale_claims()` or transitioned to `FAILED` once `attempt_count >= ARTICLE_MAX_ATTEMPTS (3)`.
- **Rejection Tracking**: Articles failing event criteria or factual quality checks are marked `REJECTED` with `reject_stage` (`LABEL` or `GATE`), `reject_reason`, and `rejected_at`.

### 3.3 Article Embeddings

Dense semantic vectors are stored directly in `articles.embedding` as a deferred `HALFVEC(2048)` column:
- **Index**: HNSW index using cosine distance:
  ```sql
  CREATE INDEX idx_articles_embedding_hnsw
  ON articles USING hnsw (embedding halfvec_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```
- **Integrity**: `ck_articles_embedding_metadata` ensures `embedding`, `embedding_model`, and `embedding_input_hash` are either all populated or all null simultaneously.

---

## 4. Article Analysis & Syndication Families

### 4.1 Article Labels (`article_labels`)

`ArticleLabel` contains structured factual metadata extracted by the LLM in `hermes-worker`. Each article has at most one valid label per prompt version:
- **Core Verification Attributes**: `is_event` (boolean), `article_type` (`BREAKING`, `DEVELOPMENT`, `ANALYSIS`, `FEATURE`, `OPINION`, `LISTICLE`, `OTHER`), `event_form` (`INCIDENT`, `PLANNED_EVENT`, `POLICY_ACTION`, `STATEMENT`, `REPORT`, `MARKET_MOVE`, `OTHER`), `certainty` (`CONFIRMED`, `REPORTED`, `ALLEGED`, `DISPUTED`).
- **Impact & Quality Scales**: `severity` (1–5), `specificity` (1–5), `consequence` (1–5), `confidence` (0.0–1.0).
- **Extracted Facts & Quotes**: `fact` (one-sentence factual claim), `scale_facts` (JSONB metric key-values), `evidence_quote` (≤400 character excerpt verified against article text).
- **Structured Entities & Locations**: JSONB arrays indexed by PostgreSQL GIN (`idx_article_labels_entities_gin`, `idx_article_labels_locations_gin`) enabling rapid entity blocking.

### 4.2 Syndication Families (`article_families`)

Wire services (Reuters, AP, AFP) are syndicated across hundreds of regional publishers. Treating each syndicated reprint as independent evidence produces artificial corroboration.

`ArticleFamily` groups identical or minimally edited syndicate copies:
- **Grouping Unit**: Syndication families represent *wire distribution*, not topic grouping.
- **Representative Article**: The earliest published article in the cluster becomes `representative_article_id`.
- **Match Criteria**: An article attaches to an existing family if:
  1. Title SimHash Hamming distance $\le 3$; OR
  2. Title SimHash distance $\le 6$ AND Body SimHash distance $\le 10$; OR
  3. Text embedding cosine similarity $\ge 0.97$;
  4. AND published within a 36-hour window.
- **Verification Impact**: When corroborating an event, multiple articles belonging to the same `family_id` count as a single piece of origin evidence.

---

## 5. Event Model & Membership Semantics

### 5.1 The Event as a Physical Pin

An `Event` represents **one physical real-world incident at a specific place and time**.
- Events are never merged across distinct incidents (e.g. two separate drone strikes in different cities remain distinct pins).
- Broad historical movements or military campaigns are represented as `Thread` records, linking individual event pins together.

### 5.2 Membership History (`event_members`)

Articles attach to events through the `event_members` join table:
- **Active Membership**: Indicated by `is_current = True`. A unique partial index enforces that an article belongs to at most one event at any time:
  ```sql
  CREATE UNIQUE INDEX uq_event_members_current_article
  ON event_members (article_id)
  WHERE is_current;
  ```
- **Historical Audit Trail**: When an article is detached, reassigned, or merged, `is_current` is set to `False` and `removed_at` is stamped.
- **Attachment Method & Provenance**: `method` records how the article was attached (`AUTO`, `LLM`, `MANUAL`), accompanied by `confidence` and `score_breakdown` (JSONB).

### 5.3 Member Hash & Description Synthesis Caching

The `Event.member_hash` column holds a SHA-256 fingerprint of the event's current active member article IDs and their facts.
- **Cluster Stage**: Attaches new member rows and leaves `member_hash` untouched (or stale).
- **Describe Stage**: Computes the SHA-256 hash of current members. If `event.member_hash == computed_hash`, the description LLM call is bypassed.
- **Synthesis Invalidation**: Whenever new articles attach or old ones detach, the hash changes, prompting `hermes-worker` to regenerate headline, summary, and locations.

### 5.4 Event Versioning & Timeline Invalidation

Each event maintains an integer `version` counter:
- **Controlled Invalidation**: `version` is incremented only when material user-facing attributes change (`ai_headline`, `ai_summary`, `location`, `category`). Minor score adjustments or non-material member joins do not bump `version`.
- **Causality Cache Alignment**: `event_timelines.event_version` stores the event version for which the Wikipedia/LLM causality timeline was synthesized. When `events.version > event_timelines.event_version`, the API or worker detects that the timeline is stale.

### 5.5 Non-Destructive Event Merging (`merged_into_id`)

When two existing events are determined to represent the same incident:
- Merged events are **never deleted**.
- The victim event has its status updated to `EventStatus.MERGED`, and its `merged_into_id` is set to the survivor's ID.
- Active members are transferred to the survivor event.
- `EventMergeService.resolve_event_id()` recursively follows redirect chains to guarantee that bookmarks, API clients, and timeline queries always resolve to the canonical active survivor.

---

## 6. Verification Engine

The verification engine (`libs/shared/hermes-db/src/hermes_db/services/verification.py`) computes an event's corroboration status purely from its current member articles and their source syndication families.

### 6.1 Status Taxonomy

| Status | Verification Rule | Weight in Scoring |
| :--- | :--- | :--- |
| `CONFIRMED` | $\ge 2$ independent origin groups agree AND $\ge 1$ Tier-1 source confirms | 1.00 |
| `CORROBORATED` | $\ge 2$ independent origin groups agree on the core fact | 0.85 |
| `SINGLE_SOURCE` | Exactly 1 independent origin group or family | 0.40 |
| `CONFLICTING` | Any member article reports `certainty == DISPUTED` | 0.25 |
| `UNVERIFIED` | Internal state: no members or no origin evidence | 0.00 |

### 6.2 Origin Group Resolution

To determine true independence, `_origin_key()` resolves each member article into an origin identifier:
1. If the article belongs to an `ArticleFamily`, use `family:{family_origin_group or family_id}`.
2. Otherwise, if the source has a configured `source_origin_group` (e.g. News Corp, Hearst), use `origin:{source_origin_group}`.
3. Otherwise, use `origin:{source_slug}`.

Ten regional newspapers publishing the exact same AP wire story share one family origin key, correctly evaluating to `SINGLE_SOURCE`.

---

## 7. Unified Importance Scoring & Selection Tiers

Hermes uses a single, authoritative, explainable `importance_score` (0–100) computed by `EventScoringService`. All legacy metrics (`trending_score`, `popularity_score`, `velocity`, `confidence`) have been removed.

### 7.1 The Scoring Formula

$$\text{importance\_score} = \text{round}(\text{base} \times \text{freshness}, 2)$$

#### 1. Base Score (0–100)
$$\text{base} = 100 \times \left( 0.40 \times \text{strength} + 0.30 \times \text{impact} + 0.15 \times \text{verify} + 0.15 \times \text{quality} \right)$$

- **Source Strength** ($\text{strength} \in [0.0, 1.0]$):
  $$\text{strength} = \min\left(1.0, \frac{\sum \text{family\_credibility}}{9.0}\right)$$
  Where the maximum credibility tier per unique origin family contributes:
  - `TIER_1` = 3.0 (e.g. Reuters, BBC, AP)
  - `TIER_2` = 2.0 (e.g. Major national dailies)
  - `TIER_3` / `TIER_4` = 1.0 (Regional / niche outlets)
- **Impact Level** ($\text{impact} \in [0.0, 1.0]$):
  - `CRITICAL` = 1.00
  - `MAJOR` = 0.80
  - `MODERATE` = 0.55
  - `MINOR` = 0.30
- **Verification Multiplier** ($\text{verify} \in [0.0, 1.0]$):
  - `CONFIRMED` = 1.00
  - `CORROBORATED` = 0.85
  - `SINGLE_SOURCE` = 0.40
  - `CONFLICTING` = 0.25
- **Reporting Quality** ($\text{quality} \in [0.5, 1.0]$):
  $$\text{quality} = \min\left(1.0, \max\left(0.5, 1.0 - 0.15 \times (5 - \text{specificity}) - 0.10 \times (5 - \text{consequence})\right)\right)$$

#### 2. Freshness Decay
$$\text{freshness} = 2^{-\frac{\text{age\_hours}}{\text{half\_life}}}$$

Age is measured against $\max(\text{latest\_published\_at}, \text{event\_time})$. Half-lives are dynamically calibrated to impact:
- `CRITICAL`: 18.0 hours
- `MAJOR`: 36.0 hours
- `MODERATE` / `MINOR`: 72.0 hours

#### 3. Single-Source Cap & Breaking Override
- **Cap**: Uncorroborated single-source events are strictly capped at $\text{importance\_score} \le 45.0$.
- **Breaking News Override**: If $\text{age} \le 2.0\text{ hours}$, `article_type == BREAKING`, $\text{impact} \ge \text{MAJOR}$, and $\text{score} \ge 45.0$, the cap is bypassed to allow high-consequence breaking stories to surface immediately on the primary map tier.

### 7.2 Selection Tiers & Hysteresis

Events are classified into map visibility tiers with a $\pm 5.0$ point hysteresis buffer to prevent UI thrashing during score decay:

```mermaid
stateDiagram-v2
    [*] --> PRIMARY : Score >= 55 (or Breaking Override)
    [*] --> FILLER : 30 <= Score < 55
    [*] --> DROP : Score < 30

    PRIMARY --> FILLER : Score < 50.0 (Demoted)
    FILLER --> PRIMARY : Score >= 55.0 (Promoted)
    FILLER --> DROP : Score < 25.0 (Dropped)
    DROP --> FILLER : Score >= 35.0 (Promoted)
```

- **PRIMARY** ($\ge 55.0$): Displayed as prominent pins at all zoom levels.
- **FILLER** ($30.0 - 55.0$): Rendered at closer zoom levels or in dense clusters.
- **DROP** ($< 30.0$): Hidden from the public map canvas.

---

## 8. Story Threads

`Thread` represents an ongoing narrative or topic aggregating multiple individual incident pins across time and geography (e.g. "Sudan Humanitarian Crisis", "2026 Global AI Summit").

### 8.1 Model Attributes & Representations

- **Identifiers**: `name` (display title) and `name_norm` (casefolded and whitespace-normalized for deterministic blocking).
- **Taxonomy**: `kind` (`DEVELOPING`, `TOPIC`).
- **Semantic Representation**: Deferred `HALFVEC(2048)` embedding and `embedding_model` capturing the composite theme of member events.
- **Extracted Aggregates**: `entities` (JSONB) and `keywords` (JSONB) for fast candidate filtering.
- **Aggregate Metrics**: `event_count` and `importance` (summed and decayed with a 168-hour / 7-day half-life).

### 8.2 Thread Lifecycle

Managed by `ThreadService.run_lifecycle()`:
- `ACTIVE` $\rightarrow$ `DORMANT`: No new events assigned for 7 days (`THREAD_DORMANT_DAYS = 7`).
- `DORMANT` $\rightarrow$ `ENDED`: No new events assigned for 30 days (`THREAD_ENDED_DAYS = 30`).
- **Reactivation**: Assigning a new incident to a `DORMANT` or `ENDED` thread immediately flips its status back to `ACTIVE`.

---

## 9. Non-Destructive Event Merge & Reconciliation

During hourly build cycles, `hermes-worker` searches for duplicate events created in separate batches. `EventMergeService` handles reconciliation without data loss.

### 9.1 Merge Execution Flow

```mermaid
sequenceDiagram
    participant Worker as hermes-worker
    participant MergeSvc as EventMergeService
    participant DB as Postgres (Session)

    Worker->>MergeSvc: merge(survivor_id, victim_id)
    MergeSvc->>DB: Reassign active EventMembers (victim -> survivor)
    MergeSvc->>DB: Set victim status = MERGED, merged_into_id = survivor_id
    MergeSvc->>DB: Reassign existing EventTl timelines
    MergeSvc->>DB: Recompute survivor aggregates & member_hash
    Note over DB: Caller commits transaction
```

1. **Resolution**: `resolve_event_id()` traces existing redirect chains to ensure neither target is already merged into another entity.
2. **Member Reassignment**: All current `event_members` belonging to the victim are updated with `event_id = survivor.id`.
3. **Status Update**: The victim event is marked `EventStatus.MERGED`, its `merged_into_id` is set to `survivor.id`, and its coordinates and summary are preserved for auditability.
4. **Timeline Migration**: Any existing `EventTl` causality timelines pointing to the victim are updated to reference the survivor.
5. **Re-aggregation**: `EventMembershipService.recompute(survivor.id)` refreshes source counts, independent origin counts, location bounding centroids, and marks `member_hash` as dirty for re-synthesis.

---

## 10. Lifecycle, Maintenance, and Retention

The `MaintenanceService` runs during daily maintenance sweeps or health checks to enforce database hygiene.

### 10.1 Daily Maintenance Stages

1. **Count Reconciliation** (`reconcile_counts`):
   Iterates through active, non-merged events and recalculates `article_count`, `source_count`, `family_count`, `independent_origin_count`, `verification_status`, and publication timestamps directly from active `event_members`.
2. **Consistency Reporting** (`consistency_report`):
   Executes high-speed subqueries checking for:
   - `count_drift`: Events whose cached counts deviate from current members.
   - `events_without_members`: Active or stale events with zero active members.
   - `missing_embeddings`: Articles marked `LABELED` missing vector embeddings.
   - `failed_claims`: Articles marked `FAILED` in the ingest queue.
   - `orphan_labels`: Labels pointing to non-existent articles.
3. **Data Retention Sweeps** (`apply_retention`):
   - **Cluster Decisions**: Purges cached pairwise LLM adjudications (`cluster_decisions`) older than 90 days.
   - **Inactive Memberships**: Purges historical `event_members` records where `is_current = False` and `removed_at < NOW() - 180 days`.
   - **Archived Embeddings**: Nulls out dense vectors on `Event.embedding` for events archived for more than 30 days, freeing storage while preserving textual and historical metadata.
4. **Article Requeueing** (`requeue_articles`):
   Allows operational resets by requeuing `FAILED` or `REJECTED` articles published after a specified timestamp back to `NEW`.

---

## 11. Schema DDL & Type Strategies

PostgreSQL enums require careful handling to avoid table locks or migration failures. Hermes employs a hybrid strategy:

### 11.1 Native PostgreSQL Enums (`native_enum=True`)

Used for fixed, low-cardinality architectural states:
- `eventstatus`: `ACTIVE`, `STALE`, `ARCHIVED`, `MERGED`
- `eventscope`: `GLOBAL`, `COUNTRY`, `STATE`, `CITY`, `LOCAL`
- `sourcetype`: `RSS`, `API`, `SCRAPE`, `GDELT`
- `sourcefeedprovider`: `PUBLISHER`, `GOOGLE_NEWS`, `GDELT`
- `sourcefetchpolicy`: `FULL_TEXT`, `SUMMARY_ONLY`

> [!NOTE]
> Modifying native PostgreSQL enums requires `ALTER TYPE ... ADD VALUE`, which cannot execute inside a transactional Alembic migration block. Such migrations use autocommit blocks (`with op.get_context().autocommit_block():`).

### 11.2 Check-Constrained Varchar Enums (`native_enum=False`)

Used for evolving taxonomies and domain classifications:
- `selection_tier`: `PRIMARY`, `FILLER`, `DROP`
- `verification_status`: `CONFIRMED`, `CORROBORATED`, `SINGLE_SOURCE`, `CONFLICTING`, `UNVERIFIED`
- `assignmentmethod`: `AUTO`, `LLM`, `MANUAL`
- `clusterdecisionkind`: `SAME`, `DIFFERENT`, `UNSURE`
- `threadkind`: `DEVELOPING`, `TOPIC`
- `threadstatus`: `ACTIVE`, `DORMANT`, `ENDED`
- `ingeststatus`: `NEW`, `NORMALIZED`, `ANALYZING`, `LABELED`, `CLUSTERED`, `REJECTED`, `FAILED`
- `articletype`: `BREAKING`, `DEVELOPMENT`, `ANALYSIS`, `FEATURE`, `OPINION`, `LISTICLE`, `OTHER`
- `eventform`: `INCIDENT`, `PLANNED_EVENT`, `POLICY_ACTION`, `STATEMENT`, `REPORT`, `MARKET_MOVE`, `OTHER`
- `articlecertainty`: `CONFIRMED`, `REPORTED`, `ALLEGED`, `DISPUTED`
- `articlecategory`: `CONFLICT`, `DISASTER`, `ECONOMY`, `POLITICS`, `TECHNOLOGY`, `SCIENCE`, `HEALTH`, `ENVIRONMENT`, `SPORTS`, `ENTERTAINMENT`, `OTHER`
- `articlebodysource`: `FULL_TEXT`, `FEED_SUMMARY`
- `rejectstage`: `LABEL`, `GATE`
- `eventtlstatus`: `READY`, `GENERATING`, `FAILED`, `NO_CONTENT`
- `impactlevel`: `CRITICAL`, `MAJOR`, `MODERATE`, `MINOR`
- `credibilitytier`: `TIER_1`, `TIER_2`, `TIER_3`, `TIER_4`

**Rationale**: Non-native enums are stored as standard `VARCHAR` columns with named `CHECK` constraints. Modifying values requires a standard `DROP CONSTRAINT` and `ADD CONSTRAINT` migration, which is fully transactional and requires zero table rewriting.

---

## 12. Complete Migration History

All migrations are maintained linearly in `libs/shared/hermes-db/migrations/versions/`:

| Revision | Down Revision | Description & Key Schema Alterations |
| :--- | :--- | :--- |
| `2ec3541646e8` | *base* | Initial schema: baseline `sources`, `articles`, `events`, PostGIS setup |
| `a1b2c3d4e5f6` | `2ec3541646e8` | Add unique constraint on `articles.url` |
| `b8446b410d52` | `a1b2c3d4e5f6` | Make `events.location` geometry nullable |
| `c1d2e3f4a5b6` | `b8446b410d52` | Create `geocode_cache` table for cached Nominatim lookups |
| `ce3d9051b570` | `c1d2e3f4a5b6` | Create `event_edges` table |
| `d159bcfd1e94` | `ce3d9051b570` | Add `lineage_target_id` to events |
| `64fc96ec0afd` | `d159bcfd1e94` | Teardown old event lineage fields and constraints |
| `db402a499ebd` | `64fc96ec0afd` | Create `story_allowlist` table |
| `67c2d30edccd` | `db402a499ebd` | Create initial `event_timeline` table |
| `e3f4a5b6c7d8` | `67c2d30edccd` | Standardize `event_timelines` schema |
| `d2e3f4a5b6c7` | `e3f4a5b6c7d8` | Add pgvector vector extension and event embeddings |
| `b1c2d3e4f5a6` | `d2e3f4a5b6c7` | Add `impact_level` and velocity to events |
| `c2d3e4f5a6b7` | `b1c2d3e4f5a6` | Add `events` PostgreSQL full-text search GIN index (`event_fts_expression`) |
| `d5e6f7a8b9c0` | `c2d3e4f5a6b7` | Create `threads` table and source health tracking |
| `9e1bb45d1cba` | `d5e6f7a8b9c0` | Harden event indexes, foreign keys, and convert timestamps to `TIMESTAMPTZ` |
| `f5a6b7c8d9e0` | `9e1bb45d1cba` | Purge null coordinate entries from `geocode_cache` |
| `e4f5a6b7c8d9` | `f5a6b7c8d9e0` | Upgrade vector columns from standard vector to `HALFVEC(2048)` |
| `c4d5e6f7a8b9` | `e4f5a6b7c8d9` | Create article ledger, `article_labels`, SimHash columns |
| `e5f6a7b8c9d0` | `c4d5e6f7a8b9` | Add article claim queue fields (`ingest_status`, `claimed_at`, `attempt_count`) |
| `f6a7b8c9d0e1` | `e5f6a7b8c9d0` | Add source feed metadata, provider enums, and `canonical_url_hash` |
| `a3b4c5d6e7f8` | `f6a7b8c9d0e1` | Add `article_families` table, deferred `articles.embedding`, SimHash indexes |
| `b4c5d6e7f8a9` | `a3b4c5d6e7f8` | Add `event_members`, `cluster_decisions`, `verification_status`, and `member_hash` |
| `c5d6e7f8a9b0` | `b4c5d6e7f8a9` | Add unified `importance_score`, `selection_tier`, score breakdowns, timeline provenance |
| `d6e7f8a9b0c1` | `c5d6e7f8a9b0` | Add thread `HALFVEC(2048)` embeddings, `name_norm`, and event counters |
| `e7f8a9b0c1d2` | `d6e7f8a9b0c1` | Add `events.merged_into_id`, `EventStatus.MERGED` enum value, and redirect indexes |
| `f8a9b0c1d2e3` | `e7f8a9b0c1d2` | **Phase 9 Cleanup**: Drop legacy ranking columns (`trending_score`, `popularity_score`, `velocity`, `confidence`, `threads.confidence`, `articles.feed_content`) |

---

## 13. Service Layer Architecture & Boundaries

The service layer is structured to enforce single-responsibility boundaries and prevent transaction entanglement:

```
src/hermes_db/services/
├── article.py             # Article CRUD, ledger queries, claim queue acquisition
├── article_analysis.py    # Article analysis persistence and status updates
├── article_family.py      # Syndication family creation, attachment, and lookup
├── article_label.py       # Article label persistence
├── cluster_decision.py    # Pairwise cluster decision caching (pair_hash)
├── event.py               # Read-side event queries (bounding box, FTS, hybrid search)
├── event_assignment.py    # Event candidate loading for article assignment
├── event_lifecycle.py     # Deterministic ACTIVE -> STALE -> ARCHIVED state machine
├── event_membership.py    # Member attachment, detachment, aggregate recalculation
├── event_merge.py         # Non-destructive event merge and redirect resolution
├── event_scoring.py       # Deterministic importance score formula and tier assignment
├── geocode.py             # Read/write access to geocode_cache
├── maintenance.py         # Count reconciliation, consistency reporting, retention sweeps
├── search.py              # Hybrid reciprocal-rank fusion and text search
├── source.py              # Source feed synchronization and status tracking
├── thread.py              # Thread CRUD, candidate ranking, and lifecycle sweeps
├── tl.py                  # Event causality timeline persistence
└── verification.py        # Independent origin derivation and status calculation
```

### 13.1 Service Guidelines

1. **Pure Async Operations**: All database operations use `AsyncSession` methods (`execute`, `scalars`, `get`).
2. **Explicit Dependency Injection**: Services accept `AsyncSession` in their constructor:
   ```python
   service = EventScoringService(session)
   await service.rescore(event_id, now=datetime.now(UTC))
   ```
3. **No Hidden Commits**: Services never invoke `session.commit()`. If an operation requires a database-generated ID (such as creating an `ArticleFamily` or `Event`), the service calls `await session.flush()`.
4. **Read vs. Write Separation**: `EventService` in `event.py` is reserved exclusively for read-side queries, spatial projections, and API responses. Event mutations belong exclusively to `EventMembershipService`, `EventScoringService`, `EventMergeService`, or `EventLifecycleService`.
