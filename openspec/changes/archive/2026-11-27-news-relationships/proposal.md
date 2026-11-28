# Proposal

## Why

Hermes currently plots related real-world news as disconnected pins and occasionally leaves near-duplicate reports unmerged on the map. For example, two reports of Pakistani astronaut Muhammad Zeeshan Ali boarding China's Tiangong space station remain two separate pins in China (`SCIENCE` vs `TECHNOLOGY`), while the related dawn watch party at SUPARCO in Islamabad, Pakistan appears completely independent; similarly, sequential diplomatic threats vs closure orders in Pyongyang and airspace incursion vs air-raid warning events in South Korea sit as unlinked items. Merging true near-duplicates while modeling and drawing explicit relationships between distinct related events lets users see causal chains, follow-ups, and cross-border reactions across the globe instead of isolated dots.

## What Changes

### Near-duplicate clustering and reconciliation
- Soften entity matching in pairwise article-to-event and event-to-event scoring so partial name variants (such as `"Muhammad Zeeshan Ali"` vs `"Zeeshan Ali"`) match instead of triggering entity vetoes, and avoid hard entity vetoes when embedding similarity is high (`>= 0.86`).
- Allow same-country `COUNTRY`/`GLOBAL`-scope events to reconcile with finer `CITY`/`LOCAL` events in the same country without triggering the `100 km` local-scope distance veto.
- Rebalance `score_event_pair` weights so zero shared syndication families no longer cap scores below auto-merge, treat shared families as an additive bonus, lower `MERGE_GRAY_THRESHOLD` from `0.85` to `0.74` so cross-category duplicates reach LLM adjudication, and widen `EVENT_RECONCILE_WINDOW_HOURS` from `24` to `48`.
- Run `ReconcileStage` before relationship discovery in `BUILD_STAGES`, evaluate event pairs with a dedicated event-to-event merge prompt (`merge-v1`) rather than article-clustering rules, and allow `RelationshipStage` `SAME_INCIDENT` detections passing safety guards to hand off to `EventMergeService.merge` automatically so missed statistical or preview-to-execution duplicates (such as `UK net migration 77,000` and `Tiangong` pre-launch vs boarding) collapse instead of being linked.

### Structured event actors (`WHO`) vs incident pin (`WHERE`)
- Retain **where** an event happened (`events.location` / `location_name` / `country_code`) strictly on the map pin while retaining **who** the actors are (`name`, `kind`, `role`, origin `location_name`/`country_code`, and Nominatim-geocoded coordinates via `hermes-ai`) in a new `events.actors` column extracted during `DescribeStage` (`describe-v5`).
- Connect cross-border actors (such as `Israel` acting on an incident pinned in `Gaza Strip`) with visually distinct dashed `Actor-Origin -> Event-Pin` vectors and non-event anchor badges — never stored as `event_relationships` or counted as separate events — while using shared `Event.actors` to recall and link related `Event <-> Event` pairs across countries.

### Pairwise event relationship graph (`news-relationships`)
- Introduce a persistent `event_relationships` graph model (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`) with canonical unordered-pair uniqueness, directionality, confidence, and a concise grounded rationale, coexisting alongside existing `Thread` topic groupings (`StoryPanel`).
- Add a structured AI relationship classifier (`RelationshipExtractor`) in `hermes-ai` that evaluates candidate pairs (including cross-border pairs sharing structured actors) and hands off `SAME_INCIDENT` detections to atomic merge rather than creating fake links between missed duplicates.
- Add `RelationshipStage` in `hermes-worker` (`BUILD_STAGES`) using pgvector cosine recall (without country or distance vetoes) plus normalized actor/entity overlap, deduplicated caching in `ClusterDecisionService`, and bounded per-run LLM budgets.
- Update `EventMergeService.merge` to repoint or deduplicate `event_relationships` when duplicate events merge.
- Expose retained `actors` and relationship counts on `MapEventResponse`, actor/connected-event details on `EventDetailResponse`, and the viewport relationship edge endpoint (`GET /api/v1/events/relationships`), synchronized with `@hermes/util-types`.

### Geodesic relationship visualization on the map
- Render viewport relationship connections by default on `MapView` as high-contrast color-coded geodesic WebGL `LineString` arcs (`CAUSED` amber, `FOLLOW_UP` cyan, `REACTION` magenta, `RELATED` violet) with an outer halo glow layer, antimeridian-safe segmentation, and a `[LINKS]` HUD toggle + inline link color legend.
- Preserve persistent type colors when an event is selected (boosting core width/opacity and glow rather than overwriting to uniform cyan), dim unrelated background arcs, render dashed cross-border `Actor -> Pin` vectors (subtle preview when `[LINKS]` is on; bright with Actor Anchor badges on selection/hover), and hide all link/actor layers cleanly in timeline mode.
- Add `ACTORS` (`WHO`) metadata and a color-coded `CONNECTED EVENTS` section in `EventPopup` with relationship type badges, rationales, and one-click camera navigation (`focusEvent`) to linked pins, plus link indicators in `ClusterList`.

### Deferred
- Traversing `event_relationships` inside conversational RAG retrieval (`event-retrieval` / `conversational-rag`).
- Replacing or consolidating existing `Thread` groupings into the relationship graph.

## Capabilities

### New Capabilities
- `event-deduplication`: Soft entity matching, broad-scope same-country tolerance, and rebalanced merge adjudication so near-duplicate articles and events merge into one canonical event pin.
- `event-relationships`: Discovery, AI classification (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`), persistence, merge cleanup, and API exposure of pairwise directed relationships between distinct events, coexisting with `Thread` groupings.
- `relationship-map-visualization`: Default-on geodesic WebGL arcs across the map viewport, `[LINKS]` HUD toggle, selected-pin ego-network highlighting, cluster link indicators, and connected-event navigation in `EventPopup`.

### Modified Capabilities
- None. Existing `news-ingestion`, `event-ranking`, `event-retrieval`, `conversational-rag`, and `chat-map-integration` specification requirements remain unchanged.

## Impact

- **`libs/shared/hermes-db`**: New `EventRelationshipType` enum, `EventRelationship` model, `events.actors` JSONB column on `Event`, `EventRelationshipService` (including actor-overlap recall), merge repointing in `EventMergeService`, bbox count/actor integration in `EventService`, and additive Alembic migrations for `event_relationships` and `events.actors`.
- **`libs/shared/hermes-ai`**: Dedicated event-merge prompt (`merge-v1`) on `PairAdjudicator`, actor extraction in `DescribeExtractor` (`describe-v5`), and new `RelationshipExtractor` (`relation-v2`), exported on `HermesAi.relationships` while preserving lazy chat import isolation.
- **`apps/hermes-worker`**: Pair-scoring and reconciliation fixes (`pair_score.py`, `reconcile.py` using `merge-v1`), actor persistence and cross-border actor origin geocoding in `DescribeStage` (exclusively via `GeocodingService`), `RelationshipStage` (`SAME_INCIDENT` auto-merge handoff + actor recall), `BUILD_STAGES` ordering update, and `RELATIONSHIP_*` + `EVENT_RECONCILE_WINDOW_HOURS` settings.
- **`apps/hermes-api` & `libs/shared/util-types`**: Updated `MapEventResponse`, `EventResponse`, and `EventDetailResponse` (adding `actors` + `relationship_count`), `GET /api/v1/events/relationships` endpoint, and hand-mirrored TypeScript types in `api-types.ts`.
- **`libs/map`**: New `useMapRelationships` hook, `relationship-geojson.ts` geodesic arc + dashed cross-border actor vector builder, halo + arc + actor WebGL layers in `map-view.tsx`, `[LINKS]` toggle + inline type legend in `MapHud`, link badges in `ClusterList`, and `ACTORS` + color-coded `CONNECTED EVENTS` navigation in `EventPopup`.
