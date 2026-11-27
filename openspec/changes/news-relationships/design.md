# Design

## Context

Hermes ingests and clusters news articles into incident-level `Event` pins (`apps/hermes-worker` -> `libs/shared/hermes-db`) and serves them to a full-bleed Mapbox GL interface (`apps/hermes-api` -> `libs/map`). See `proposal.md` for motivation and `specs/` for behavioral requirements.

Several existing constraints shape this design:
- **Worker execution budget and memory**: `hermes-worker` runs as a run-and-die 512 MB RAM Fargate batch task bounded by `MAX_LLM_CALLS_PER_RUN = 120` and `RPM_LIMIT = 26`. Any cross-event analysis must avoid $O(N^2)$ LLM sweeps.
- **Current deduplication bottlenecks**: `pair_score.py` enforces exact normalized string equality on entities, vetoes on distance `> 100 km` in `_event_location_match` regardless of `COUNTRY`/`GLOBAL` scope, and assigns `0.10` merge weight to `shared_families` (making `0.90` the ceiling for disjoint-family duplicates vs `MERGE_AUTO_THRESHOLD = 0.92`, and dropping cross-category duplicates below `MERGE_GRAY_THRESHOLD = 0.85`).
- **Single-parent `Thread` model**: `Event.thread_id` is a single nullable foreign key (`1:N`), and `ThreadStage` groups new threads by `(category, sorted_entities[0], sorted_entities[1])`. This cannot represent typed many-to-many links (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`) across categories and countries.
- **Library boundaries**: `hermes-db` must remain free of LLM clients; `hermes-ai` must remain free of `hermes-db` imports and keep LangChain/LangGraph lazy-loaded; `apps/hermes-api` schemas must stay mirrored in `libs/shared/util-types`; `libs/map` must render purely via Mapbox GL WebGL layers driven by `useMapStore`.

## Goals / Non-Goals

**Goals:**
- Collapse near-duplicate incidents (such as same-incident reports across `SCIENCE`/`TECHNOLOGY`, partial person names, or country-centroid vs city-level pins) inside `ClusterStage` / `ReconcileStage` before relationship discovery runs.
- Persist a directed, canonical-pair `event_relationships` graph coexisting independently alongside `Thread` groupings.
- Discover cross-continental and co-located relationships using existing `HALFVEC(2048)` pgvector embeddings and soft entity overlap without geographic distance vetoes, caching evaluations in `cluster_decisions`.
- Expose relationship counts, event-detail connections, and viewport relationship edges (including off-screen counterpart coordinates) via `hermes-api` and `@hermes/util-types`.
- Render default-on curved geodesic arcs on Mapbox GL with a `[LINKS]` HUD toggle, selected-pin ego-network highlighting, cluster link badges, and one-click `focusEvent` navigation.

**Non-Goals:**
- Replacing or migrating existing `Thread` records or `StoryPanel` UI.
- Traversing `event_relationships` inside conversational RAG retrieval (`SearchService` / `DbChatRetriever`).
- Modifying `EventTl` (Wikipedia historical timeline synthesis).
- Introducing persistent background workers inside `hermes-api` or new npm/Python dependencies.

## Decisions

### 1. Soft entity overlap and syndication-neutral merge scoring (`pair_score.py`, `event_merge.py`)

**Decision:** Keep near-duplicate merging strictly inside `ClusterStage` and `ReconcileStage` rather than letting `RelationshipStage` perform merges. Fix the three root causes in `pair_score.py`:
1. **Soft entity matching**: Tokenize normalized entity names (`_normalize_name`) and match exact strings (`1.0`), multi-token subset containment (`len(shorter_tokens) >= 2` and `shorter_tokens <= longer_tokens`, e.g., `"zeeshan ali"` inside `"muhammad zeeshan ali"` -> `0.85`), or token Jaccard `>= 0.6` (`0.85`). Bypass the hard `"entities"` veto whenever embedding cosine similarity `>= 0.86`.
2. **Scope-aware same-country location matching**: Add `scope: EventScope` to `EventPairState`. In `_event_location_match`, when `left.country_code == right.country_code` and either event has `scope in {COUNTRY, GLOBAL}`, score location as `0.6` instead of applying the `100 km` distance veto. Preserve the `100 km` veto when both events are `CITY` or `LOCAL`.
3. **Additive family bonus & lowered gray band**: Rebalance `score_event_pair` base weights to sum to `1.0` without requiring shared syndication families (`embedding=0.45`, `entities=0.22`, `location=0.15`, `time=0.13`, `category=0.05`), add `family_bonus = 0.08 * min(1.0, shared_families / 2.0)` clamped at `1.0`, set `MERGE_GRAY_THRESHOLD = 0.74`, `MERGE_AUTO_THRESHOLD = 0.90`, and widen `EVENT_RECONCILE_WINDOW_HOURS` from `24` to `48`.

**Alternatives considered:**
- *Auto-merging inside `RelationshipStage` when the classifier outputs `SAME_INCIDENT`*: Rejected because merging mutates event membership, invalidates descriptions (`member_hash = None`), and triggers rescoring; keeping `ReconcileStage` before `RelationshipStage` in `BUILD_STAGES` preserves single responsibility and ensures `DescribeStage`/`ScoreStage`/`RelationshipStage` never operate on unmerged duplicates on subsequent runs.
- *Lowering `AUTO_ATTACH_THRESHOLD` aggressively*: Rejected because auto-attaching without LLM review increases false merges for same-city sequential escalations (such as Pyongyang threat vs embassy closure order).

### 2. Dedicated `event_relationships` graph coexisting with `threads` (`hermes-db`)

**Decision:** Add an `event_relationships` table (`EventRelationship` ORM model) with `source_event_id`, `target_event_id`, `relationship_type` (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED` stored as `native_enum=False`), `confidence`, `rationale` (`String(300)`), and `pair_hash` (`String(64)`). Enforce at most one canonical edge per unordered pair via:
- `CheckConstraint("source_event_id <> target_event_id")`
- Unique functional index `uq_event_relationships_unordered_pair` on `(LEAST(source_event_id, target_event_id), GREATEST(source_event_id, target_event_id))`

Reuse `cluster_decisions` (with a `"rel|"` domain prefix inside the SHA-256 `pair_hash`) to cache negative (`NONE` -> `ClusterDecisionKind.DIFFERENT`) and duplicate-guard (`SAME_INCIDENT` -> `ClusterDecisionKind.SAME`) outcomes so unchanged pairs skip LLM evaluation and inherit the existing 90-day retention cleanup in `MaintenanceService.apply_retention()`.

**Alternatives considered:**
- *Replacing or overloading `Thread` (`Event.thread_id`)*: Rejected because `Event.thread_id` is a single nullable FK (`1:N` tree), whereas relationships form a typed many-to-many graph (`N:M`) and the user explicitly wants threads to coexist.
- *Adding a separate `relationship_decisions` cache table*: Unnecessary; `cluster_decisions` is already content-addressed by SHA-256 `pair_hash` and purged after 90 days by maintenance.

### 3. Two-stage relationship discovery funnel (`hermes-ai` + `hermes-worker`)

**Decision:** Place `RelationshipStage` in `BUILD_STAGES` immediately after `ReconcileStage`:
`ClusterStage -> DescribeStage -> ScoreStage -> ReconcileStage -> RelationshipStage -> ThreadStage`.

1. **Candidate Recall (0 LLM calls)**: Select up to `RELATIONSHIP_EVENT_LIMIT = 100` recent `ACTIVE` unmerged events (`selection_tier != DROP`). Recall up to `RELATIONSHIP_NEIGHBORS_PER_EVENT = 8` candidates per anchor within `RELATIONSHIP_WINDOW_DAYS = 10` using pgvector cosine similarity (`>= 0.62`, no geographic or country veto) unioned with in-memory soft entity matches across the active pool, deduplicated by unordered pair `(min_id, max_id)`.
2. **Cache Check**: Compute `pair_hash` from `"rel"`, sorted IDs, each event's `member_hash or str(version)`, and `RELATIONSHIP_PROMPT_VERSION` (`"relation-v1"`). Skip pairs already persisted in `event_relationships` with matching `pair_hash` or present in `cluster_decisions`.
3. **Batched Classification**: Construct `RelationshipExtractor` in `hermes-ai` (using route `"relationship"` with fallback to `LLM_MODEL`, untrusted XML boundary wrapping, `@observe(..., capture_input=False, capture_output=False)`). Evaluate batches of `RELATIONSHIP_BATCH_SIZE = 8` capped at `RELATIONSHIP_LLM_PAIRS_PER_RUN = 30`, reserving `JobContext.budget` calls upfront. Persist outcomes in `{CAUSED, FOLLOW_UP, REACTION, RELATED}` with `confidence >= 0.70`, inverting `source_event_id`/`target_event_id` when `direction == RIGHT_TO_LEFT`. Reject `SAME_INCIDENT` and `NONE` without creating edges.

**Alternatives considered:**
- *Evaluating all active pairs ($O(N^2)$)*: Rejected due to LLM budget (`MAX_LLM_CALLS_PER_RUN = 120`) and latency limits.
- *Linking purely by embedding threshold without LLM verification*: Rejected because topically similar independent events (e.g., two unrelated earthquakes) share high vector similarity without having a causal or narrative link.

### 4. Merge repointing (`EventMergeService.merge`)

**Decision:** Extend `EventMergeService.merge` inside its existing transaction so when `loser_id` merges into `survivor_id`:
1. Any edge directly connecting `survivor_id` and `loser_id` is deleted.
2. Any remaining edge referencing `loser_id` and some third event `X` is repointed to `survivor_id` unless an edge between `survivor_id` and `X` already exists, in which case the `loser_id <-> X` row is deleted.

This preserves graph integrity without cascading away valid cross-border links when a duplicate cluster collapses.

### 5. API & TypeScript contract design (`hermes-api` + `@hermes/util-types`)

**Decision:**
- Add `relationship_count: int = 0` to `MapEventResponse` and `EventResponse`, populated via a single batched `COUNT`/`GROUP BY` query in `EventRelationshipService.counts_for_events(...)` during `GET /api/v1/events/bbox` and `GET /api/v1/events/`.
- Add `relationships: list[EventRelationshipItem] = []` directly to `EventDetailResponse` (`GET /api/v1/events/{event_id}`), returning counterpart coordinates, headline, category color, direction (`OUTGOING`/`INCOMING`), relationship type, and rationale with zero extra client roundtrip on pin click.
- Add `GET /api/v1/events/relationships` (registered before `/{event_id}` to avoid UUID path matching) accepting clamped `north`, `south`, `east`, `west` query params and returning `list[MapRelationshipEdgeResponse]` for every active edge touching at least one visible event in the bbox, including coordinates for out-of-viewport counterparts so cross-border arcs (China `<-->` Pakistan) draw across screen edges.
- Hand-mirror all schemas in `libs/shared/util-types/src/lib/api-types.ts`.

**Alternatives considered:**
- *Fetching relationships only when a pin is clicked*: Rejected because the user requested viewport relationship arcs to be visible by default on map load.

### 6. Geodesic WebGL rendering & HUD interaction (`@hermes/map`)

**Decision:**
- Add `showRelationships: boolean` (default `true`) and `toggleRelationships()` to `useMapStore`, and `useMapRelationships()` hook backed by TanStack Query.
- Build a pure helper `relationship-geojson.ts` that converts `MapRelationshipEdgeResponse[]` (plus `selectedEvent.relationships` when selected, deduplicated by edge `id`) into:
  - `edgesGeoJson`: 24-point spherical great-circle arcs (`LineString` / `MultiLineString`), split cleanly if a segment crosses the antimeridian (`|deltaLng| > 180°`) so lines never streak across the entire map.
  - `partnersGeoJson`: `Point` features for counterparts of `selectedEventId` (so even clustered or off-screen targets show a highlight ring).
- Register Mapbox WebGL sources (`relationship-edges-source`, `relationship-partners-source`) and layers (`hermes-relationship-arcs`, `hermes-relationship-partners`) inside `map-view.tsx`:
  - Baseline when `showRelationships` is `true` and nothing is selected: dashed arcs at `line-opacity: 0.32`, colored by relationship type (`#ffb454` for `CAUSED`, `#00f0ff` for `FOLLOW_UP`/`REACTION`, `#0aa5b1` for `RELATED`).
  - When `selectedEventId` is active: touching arcs brighten (`line-opacity: 0.95`, width `2.2`) even if `showRelationships` is toggled off; unrelated background arcs dim (`line-opacity: 0.12`).
  - In timeline mode (`isTlMode`), hide both relationship layers alongside the event pin layers.
- Add `[LINKS]` toggle button in `MapHud`, compact `N LINKS` indicators in `ClusterList` (and outer accent ring via Mapbox expression on `hermes-unclustered-point` when `relationship_count > 0`), and a `CONNECTED EVENTS` section in `EventPopup` whose items call `focusEvent(related_event_id, [related_longitude, related_latitude])`.

**Alternatives considered:**
- *Straight 2-point Mercator lines*: Rejected because long-haul connections (East Asia <-> South Asia <-> Europe) look flat and distort relative to globe distance compared to spherical great-circle arcs.

## Risks / Trade-offs

- **Visual density at world zoom** → Default background arc opacity is kept low (`0.32`), dims further (`0.12`) when inspecting a pin, and can be toggled off anytime via `[LINKS]` in `MapHud`.
- **LLM call budget consumption** → `RelationshipStage` runs after `ClusterStage`/`DescribeStage`/`ReconcileStage` and enforces `RELATIONSHIP_LLM_PAIRS_PER_RUN = 30` alongside `ClusterDecision` pair-hash caching; if `MAX_LLM_CALLS_PER_RUN` is reached, committed batches persist safely and remaining pairs roll over to the next run.
- **Unclustered/clustered pin overlap for same-city relationships** → When two linked events share coordinates (Pyongyang, South Korea), arcs have zero spatial length, so `ClusterList` surfaces `N LINKS` indicators and `EventPopup` lists the `CONNECTED EVENTS` directly with click-to-switch selection.
- **Duplicate merge side-effects on existing relationships** → Handled atomically inside `EventMergeService.merge` so merged losers never leave dangling or self-looping edges.

## Migration Plan

1. Generate an additive Alembic revision via `npx nx run hermes-db:makemigrations -- -m "add event relationships"` creating `event_relationships` and its constraints/indexes (`uq_event_relationships_unordered_pair`, `idx_event_relationships_source`, `idx_event_relationships_target`).
2. Apply migration with user approval (`npx nx run hermes-db:migrate`) before deploying `hermes-worker` and `hermes-api`.
3. Rollback path: `alembic downgrade -1` cleanly drops `event_relationships` without touching existing `events`, `threads`, or `cluster_decisions` tables; old worker/API revisions continue functioning unaffected.
