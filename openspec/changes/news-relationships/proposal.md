# Proposal

## Why

Hermes currently plots related real-world news as disconnected pins and occasionally leaves near-duplicate reports unmerged on the map. For example, two reports of Pakistani astronaut Muhammad Zeeshan Ali boarding China's Tiangong space station remain two separate pins in China (`SCIENCE` vs `TECHNOLOGY`), while the related dawn watch party at SUPARCO in Islamabad, Pakistan appears completely independent; similarly, sequential diplomatic threats vs closure orders in Pyongyang and airspace incursion vs air-raid warning events in South Korea sit as unlinked items. Merging true near-duplicates while modeling and drawing explicit relationships between distinct related events lets users see causal chains, follow-ups, and cross-border reactions across the globe instead of isolated dots.

## What Changes

### Near-duplicate clustering and reconciliation
- Soften entity matching in pairwise article-to-event and event-to-event scoring so partial name variants (such as `"Muhammad Zeeshan Ali"` vs `"Zeeshan Ali"`) match instead of triggering entity vetoes, and avoid hard entity vetoes when embedding similarity is high (`>= 0.86`).
- Allow same-country `COUNTRY`/`GLOBAL`-scope events to reconcile with finer `CITY`/`LOCAL` events in the same country without triggering the `100 km` local-scope distance veto.
- Rebalance `score_event_pair` weights so zero shared syndication families no longer cap scores below auto-merge, treat shared families as an additive bonus, lower `MERGE_GRAY_THRESHOLD` from `0.85` to `0.74` so cross-category duplicates reach LLM adjudication, and widen `EVENT_RECONCILE_WINDOW_HOURS` from `24` to `48`.
- Run `ReconcileStage` before relationship discovery in `BUILD_STAGES` so near-duplicate pins collapse before relationships are evaluated.

### Pairwise event relationship graph (`news-relationships`)
- Introduce a persistent `event_relationships` graph model (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`) with canonical unordered-pair uniqueness, directionality, confidence, and a concise grounded rationale, coexisting alongside existing `Thread` topic groupings (`StoryPanel`).
- Add a structured AI relationship classifier (`RelationshipExtractor`) in `hermes-ai` that evaluates candidate pairs and explicitly rejects `SAME_INCIDENT` pairs rather than creating fake links between missed duplicates.
- Add `RelationshipStage` in `hermes-worker` (`BUILD_STAGES`) using pgvector cosine recall (without country or distance vetoes) plus soft entity overlap, deduplicated caching in `ClusterDecisionService`, and bounded per-run LLM budgets.
- Update `EventMergeService.merge` to repoint or deduplicate `event_relationships` when duplicate events merge.
- Expose relationship counts on `MapEventResponse`, connected-event details on `EventDetailResponse`, and a viewport relationship edge endpoint (`GET /api/v1/events/relationships`), synchronized with `@hermes/util-types`.

### Geodesic relationship visualization on the map
- Render viewport relationship connections by default on `MapView` as curved geodesic WebGL `LineString` arcs (with antimeridian-safe segmentation) and a `[LINKS]` visibility toggle in `MapHud`.
- Brighten an event's ego-network arcs and highlight connected partner pins (including out-of-viewport counterparts) when an event is selected, dim unrelated background arcs, and hide relationship layers cleanly in timeline mode.
- Add a `CONNECTED EVENTS` section in `EventPopup` showing relationship type badges, rationales, and one-click camera navigation (`focusEvent`) to linked pins, plus link indicators in `ClusterList`.

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

- **`libs/shared/hermes-db`**: New `EventRelationshipType` enum, `EventRelationship` model, `EventRelationshipService`, merge repointing in `EventMergeService`, bbox count integration in `EventService`, and one Alembic migration adding `event_relationships`.
- **`libs/shared/hermes-ai`**: New `RelationshipExtractor`, Pydantic models, and `RELATIONSHIP_SYSTEM_PROMPT` (`relation-v1`), exported on `HermesAi.relationships` while preserving lazy chat import isolation.
- **`apps/hermes-worker`**: Pair-scoring and reconciliation fixes (`pair_score.py`, `reconcile.py`), new `RelationshipStage`, `BUILD_STAGES` ordering update (`ReconcileStage` -> `RelationshipStage` -> `ThreadStage`), and new `RELATIONSHIP_*` + `EVENT_RECONCILE_WINDOW_HOURS` settings.
- **`apps/hermes-api` & `libs/shared/util-types`**: Updated `MapEventResponse` and `EventDetailResponse`, new `GET /api/v1/events/relationships` endpoint, and hand-mirrored TypeScript types in `api-types.ts`.
- **`libs/map`**: New `useMapRelationships` hook, `relationship-geojson.ts` geodesic arc builder, Mapbox arc/partner layers in `map-view.tsx`, `[LINKS]` toggle in `MapHud`, link badges in `ClusterList`, and `CONNECTED EVENTS` navigation in `EventPopup`.
