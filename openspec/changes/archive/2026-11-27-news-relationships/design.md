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

**Decision:** Combine dedicated event-to-event merge adjudication in `ReconcileStage` (`merge-v1`) with safety-guarded `SAME_INCIDENT` auto-merge handoff inside `RelationshipStage`:
1. **Soft entity & actor matching**: Tokenize normalized entity/actor names (`_normalize_name`) and match exact strings (`1.0`), multi-token subset containment (`len(shorter_tokens) >= 2` and `shorter_tokens <= longer_tokens`, e.g., `"zeeshan ali"` inside `"muhammad zeeshan ali"` -> `0.85`), or token Jaccard `>= 0.6` (`0.85`). Include retained `Event.actors` alongside `ArticleLabel.entities` so events whose older labels lacked entities still match cleanly. Bypass the hard `"entities"` veto whenever embedding cosine similarity `>= 0.86`.
2. **Scope-aware same-country location matching**: Add `scope: EventScope` to `EventPairState`. In `_event_location_match`, when `left.country_code == right.country_code` and either event has `scope in {COUNTRY, GLOBAL}`, score location as `0.6` instead of applying the `100 km` distance veto. Preserve the `100 km` veto when both events are `CITY` or `LOCAL`.
3. **Additive family bonus, lowered gray band & dedicated `merge-v1` prompt**: Rebalance `score_event_pair` base weights (`embedding=0.45`, `entities=0.22`, `location=0.15`, `time=0.13`, `category=0.05`), add `family_bonus = 0.08 * min(1.0, shared_families / 2.0)` clamped at `1.0`, set `MERGE_GRAY_THRESHOLD = 0.74`, `MERGE_AUTO_THRESHOLD = 0.90`, and widen `EVENT_RECONCILE_WINDOW_HOURS` to `48`. Give `PairAdjudicator` a dedicated `decide_merge()` / `PAIR_MERGE_SYSTEM_PROMPT` (`merge-v1`) tailored to comparing two synthesized event cards so multi-outlet reporting of the exact same release (`UK net migration 77,000` with differing secondary entities like `Home Office` vs `Liberal Democrats`) and preview-to-execution progression of the exact same single event (`Tiangong` set to launch vs boarded) return `SAME`, while keeping distinct local reactions (Islamabad crowds watching) `DIFFERENT`.
4. **Guarded `SAME_INCIDENT` auto-merge in `RelationshipStage`**: When `RelationshipStage` classifies an unmerged pair as `SAME_INCIDENT` (`confidence >= RELATIONSHIP_MIN_CONFIDENCE`) and safety guards pass (both events active/stale, unmerged, distinct IDs, and deterministic survivor chosen by article count/importance/earliest report without conflicting active thread assignments), invoke `EventMergeService.merge` immediately, delete any prior `event_relationships` edge between them, and let subsequent describe/score passes refresh the survivor.

**Alternatives considered:**
- *Keeping `adjudicate-v1` (article-clustering prompt) inside `ReconcileStage`*: Rejected after live verification showed `adjudicate-v1`'s article-vs-event framing and strict Rule 4 caused `UK migration 77k` (`0.7953`) and `China Tiangong` (`0.7584`) to reject merge as `DIFFERENT (0.95)`, only for `relation-v1` to link them as `RELATED`/`FOLLOW_UP`.
- *Suppressing `SAME_INCIDENT` edges in `RelationshipStage` without merging*: Rejected because pairs recalled across wider windows or actor overlap outside `ReconcileStage` would otherwise linger as unmerged duplicates on the map.

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

1. **Candidate Recall (0 LLM calls)**: Select up to `RELATIONSHIP_EVENT_LIMIT = 100` recent `ACTIVE` unmerged events (`selection_tier != DROP`). Recall up to `RELATIONSHIP_NEIGHBORS_PER_EVENT = 8` candidates per anchor within `RELATIONSHIP_WINDOW_DAYS = 10` using pgvector cosine similarity (`>= 0.62`, no geographic or country veto) unioned with in-memory soft entity overlap (`_ENTITY_RECALL_MIN_COSINE = 0.50` for single generic entities) and normalized retained-actor (`Event.actors`) matches across differing locations without requiring high embedding similarity (allowing cross-border links like `Israel` strikes in `Gaza Strip` <-> `Israel` prisoner policy even when cosine sits near `0.25`), bounded per anchor and deduplicated by unordered pair `(min_id, max_id)`.
2. **Cache Check**: Compute `pair_hash` from `"rel"`, sorted IDs, each event's `member_hash or str(version)`, and `RELATIONSHIP_PROMPT_VERSION` (`"relation-v2"`). Skip pairs already persisted in `event_relationships` with matching `pair_hash` or present in `cluster_decisions`.
3. **Batched Classification**: Construct `RelationshipExtractor` in `hermes-ai` (using route `"relationship"` with fallback to `LLM_MODEL`, untrusted XML boundary wrapping, `@observe(..., capture_input=False, capture_output=False)`), passing each side's retained `actors` (`WHO`) alongside `location` (`WHERE`). Evaluate batches of `RELATIONSHIP_BATCH_SIZE = 8` capped at `RELATIONSHIP_LLM_PAIRS_PER_RUN = 30`, reserving `JobContext.budget` calls upfront. Persist outcomes in `{CAUSED, FOLLOW_UP, REACTION, RELATED}` with `confidence >= 0.70`, inverting `source_event_id`/`target_event_id` when `direction == RIGHT_TO_LEFT`. Hand off `SAME_INCIDENT` outcomes passing safety guards to `EventMergeService.merge` and cache rejected `NONE` outcomes as `DIFFERENT`.

**Alternatives considered:**
- *Evaluating all active pairs ($O(N^2)$)*: Rejected due to LLM budget (`MAX_LLM_CALLS_PER_RUN = 120`) and latency limits.
- *Linking purely by embedding threshold without LLM verification*: Rejected because topically similar independent events (e.g., two unrelated earthquakes) share high vector similarity without having a causal or narrative link.

### 4. Merge repointing (`EventMergeService.merge`)

**Decision:** Extend `EventMergeService.merge` inside its existing transaction so when `loser_id` merges into `survivor_id`:
1. Any edge directly connecting `survivor_id` and `loser_id` is deleted.
2. Any remaining edge referencing `loser_id` and some third event `X` is repointed to `survivor_id` unless an edge between `survivor_id` and `X` already exists, in which case the `loser_id <-> X` row is deleted.

This preserves graph integrity without cascading away valid cross-border links when a duplicate cluster collapses.

### 5. Structured `WHO` Actors & `WHERE` Pin Separation (`hermes-db`, `hermes-ai`, `hermes-worker`)

**Decision:** Retain incident site (**WHERE**) and normalized actors (**WHO**) separately on `Event`:
1. **Incident Pin (`WHERE`)**: `_geocode_event` continues pinning `events.location`, `location_name`, `country_code` strictly to the primary incident location (`locations[0]`, e.g., `Gaza Strip`, `PS`), never moving an event pin onto an external actor's country.
2. **Actor Retention (`WHO`)**: Add an additive `actors` JSONB column on `events` (`EventActor` objects with `name`, `kind` in `STATE | ORGANIZATION | PERSON | GROUP`, `role` in `ACTOR | TARGET | PARTICIPANT`, optional `location_name` & `country_code`, and cached Nominatim-geocoded `latitude`/`longitude`). Extend `EventDescription` (`describe-v5`) so `DescribeStage` extracts structured actors (resolving demonyms such as `"Israeli attacks"` -> state actor `"Israel"`, `country_code="IL"`) and resolves cross-border actor origin locations exclusively through `hermes-ai`'s cached rate-limited `GeocodingService` (never LLM-generated coordinates).
3. **No Fake Second Events**: Intra-event actor involvements (such as `Israel -> Gaza Strip` within a single strike report) are stored on the event's `actors` payload rather than inserted into `event_relationships` or incremented into `relationship_count`.

**Alternatives considered:**
- *Creating synthetic `Event` records for external actors*: Rejected because one event pin should not duplicate across countries or pollute event counts.
- *Reading only `ArticleLabel.entities` at relationship discovery time*: Rejected because generic entity lists conflate locations/passersby with primary actors, drop demonyms like `"Israeli"`, and are empty on older articles.

### 6. API & TypeScript contract design (`hermes-api` + `@hermes/util-types`)

**Decision:**
- Add `relationship_count: int = 0` and `actors: list[EventActorItem] = []` to `MapEventResponse` and `EventResponse`, populated in `EventService` during `GET /api/v1/events/bbox` and `GET /api/v1/events/`.
- Add `relationships: list[EventRelationshipItem] = []` (and inherited `actors`) to `EventDetailResponse` (`GET /api/v1/events/{event_id}`), returning counterpart coordinates, headline, category color, direction (`OUTGOING`/`INCOMING`), relationship type, and rationale alongside structured actors.
- Keep `GET /api/v1/events/relationships` returning `list[MapRelationshipEdgeResponse]` (preserving its array contract) accepting clamped `north`, `south`, `east`, `west` query params and returning active `Event <-> Event` edges touching at least one visible event in the bbox, including coordinates for out-of-viewport counterparts so cross-border arcs (China `<-->` Pakistan) draw across screen edges.
- Hand-mirror all schemas (`EventActorKind`, `EventActorRole`, `EventActorItem`, updated event models) in `libs/shared/util-types/src/lib/api-types.ts`.

**Alternatives considered:**
- *Changing `/events/relationships` response from an array to an envelope object*: Rejected to preserve backward-compatible array semantics while delivering viewport actor vector data directly on `MapEventResponse[]`.

### 7. High-contrast neon styling & cross-border actor vectors (`@hermes/map`)

**Decision:**
- Add `showRelationships: boolean` (default `true`) and `toggleRelationships()` to `useMapStore`, and `useMapRelationships()` hook backed by TanStack Query.
- Extend `relationship-geojson.ts` cleanly with pure helpers converting `MapRelationshipEdgeResponse[]` + visible `MapEventResponse[]` (for cross-border actors whose geocoded origin differs from the event pin location and country/coordinates) into:
  - `edgesGeoJson`: 24-point spherical great-circle arcs (`LineString`), antimeridian-split.
  - `partnersGeoJson`: `Point` features for counterparts of `selectedEventId`.
  - `actorVectorsGeoJson` & `actorAnchorsGeoJson`: dashed geodesic vectors connecting cross-border `ACTOR` coordinates to their event `WHERE` pin (`is_active` flagged on selection/hover), plus non-event diamond/ring Actor Anchor point features for active/hovered events.
- Upgrade Mapbox WebGL layers in `map-view.tsx` (`hermes-relationship-arcs-glow`, `hermes-relationship-arcs`, `hermes-relationship-partners`, `hermes-actor-vectors`, `hermes-actor-anchors`):
  - **Persistent high-contrast neon palette** preserved across BOTH inactive and selected states (never overriding `is_active` arcs to uniform `#00f0ff`): `CAUSED` amber (`#ffb454`), `FOLLOW_UP` electric cyan (`#00f0ff`), `REACTION` vivid magenta (`#ff4fd8`), `RELATED` electric violet (`#b388ff`), and cross-border `ACTOR` vectors crisp ice-white/lime dashed (`#e2f1ff`).
  - **Outer glow + raised baseline opacity**: Render `hermes-relationship-arcs-glow` underneath crisp `hermes-relationship-arcs` (`line-opacity` ~`0.70`, width `2.0` baseline; `1.0` opacity and width `3.2` + stronger halo when selected/hovered; `0.14` dimmed when another pin is selected).
  - **Actor vector visibility**: When `[LINKS]` is toggled ON and no event is selected, draw subtle dim dashed actor vectors without standalone actor anchor markers; when an event is selected/hovered, illuminate its cross-border actor vectors and show non-event diamond/ring Actor Anchor markers; hide all relationship and actor layers in timeline mode (`isTlMode`).
- Add `[LINKS]` toggle + compact relationship-type color legend in `MapHud` (visible when links are enabled), color-coded type badges in `EventPopup` `CONNECTED EVENTS`, an `ACTORS` (`WHO`) section in `EventPopup`, and `N LINKS` indicators in `ClusterList`.

**Alternatives considered:**
- *Overriding all selected edges to `#00f0ff`*: Rejected because users could no longer tell whether a selected connection was `CAUSED`, `FOLLOW_UP`, `REACTION`, or `RELATED`.
- *Plotting permanent bright markers for every external actor*: Rejected to keep global map views uncluttered until an event is inspected.

## Risks / Trade-offs

- **Visual density at world zoom** → Actor anchor markers stay hidden until an event is selected/hovered, baseline actor vectors render softly dashed when `[LINKS]` is ON, background Event↔Event arcs dim to `~0.14` during pin inspection, and everything toggles cleanly via `[LINKS]` in `MapHud`.
- **LLM call budget consumption** → `RelationshipStage` runs after `ClusterStage`/`DescribeStage`/`ReconcileStage` and enforces `RELATIONSHIP_LLM_PAIRS_PER_RUN = 30` alongside `ClusterDecision` pair-hash caching; actor origin geocoding reuses `geocode_cache` and obeys the `1 req/s` Nominatim bucket.
- **Unclustered/clustered pin overlap for same-city relationships** → When two linked events share coordinates (Pyongyang, South Korea), arcs have zero spatial length, so `ClusterList` surfaces `N LINKS` indicators and `EventPopup` lists `CONNECTED EVENTS` directly with click-to-switch selection.
- **Duplicate merge side-effects on existing relationships** → Handled atomically inside `EventMergeService.merge` (both from `ReconcileStage` and guarded `RelationshipStage` `SAME_INCIDENT` handoffs) so merged losers never leave dangling or self-looping edges.

## Migration Plan

1. *(Applied)* Additive Alembic revision `33ae8a869e4e` adding `event_relationships` (`uq_event_relationships_unordered_pair`, `idx_event_relationships_source`, `idx_event_relationships_target`).
2. Generate a second additive Alembic revision via `npx nx run hermes-db:makemigrations -- -m "add event actors"` adding `events.actors` (`JSONB`, server default `'[]'`, nullable false).
3. Apply migration with user approval (`npx nx run hermes-db:migrate`) before running updated `hermes-worker` / `hermes-api`.
4. Prompt versions bump cleanly (`describe-v5`, `merge-v1`, `relation-v2`), allowing deterministic local refresh (`describe` -> `reconcile` -> `relationship`) of existing recent events (`Tiangong`, `UK Migration 77k`, `Gaza/Israel`).
5. Rollback path: `alembic downgrade -1` cleanly drops `events.actors` without affecting `event_relationships`, `events`, `threads`, or `cluster_decisions`.
