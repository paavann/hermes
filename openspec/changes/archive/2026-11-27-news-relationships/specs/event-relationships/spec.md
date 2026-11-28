# Spec Delta

## Purpose

Discovers, classifies, persists, and exposes typed directed relationships between distinct plotted news events so users and downstream clients can trace causal chains, escalations, and cross-border reactions across the globe.

## ADDED Requirements

### Requirement: Typed directed pairwise event relationships
The system SHALL persist at most one canonical directional relationship per unordered pair of distinct events, typed as `CAUSED`, `FOLLOW_UP`, `REACTION`, or `RELATED`, with a `0.0`–`1.0` confidence score and a grounded rationale of at most `300` characters.

#### Scenario: Cross-border reaction linked to primary event
- **WHEN** an event in China reports an astronaut boarding Tiangong and an event in Islamabad reports students watching the launch at SUPARCO
- **THEN** the system stores one directional `REACTION` relationship from the Islamabad event to the China event with its rationale

#### Scenario: Temporal escalation linked in sequence
- **WHEN** an earlier event reports North Korea threatening to close a Swiss embassy and a later event reports North Korea ordering its closure
- **THEN** the system stores one directional `FOLLOW_UP` relationship from the threat event to the closure event

#### Scenario: Self-loops and reversed duplicate edges rejected
- **WHEN** the system attempts to persist an edge where both endpoints match or where an edge already exists in the opposite direction between the same two events
- **THEN** self-referential edges are rejected and opposite-direction updates replace or normalize into the single canonical pair record

### Requirement: Cross-location candidate recall without geographic vetoes
Relationship discovery SHALL recall candidate pairs for recent active non-dropped events using semantic vector similarity of at least `0.62`, soft article-entity overlap (with cosine floor `>= 0.50` for single generic entity matches), OR normalized retained `WHO` actor overlap across differing locations without geographic vetoes or high cosine blockers when both events share concrete actors.

#### Scenario: Cross-continental pair recalled
- **WHEN** an active event in Beijing and an active event in Islamabad share entity/actor overlap (`"Zeeshan Ali"`) or vector similarity `>= 0.62`
- **THEN** both events are paired for relationship evaluation despite lying in different countries over `3,000 km` apart

#### Scenario: Regional cause-and-effect pair recalled
- **WHEN** an event on a South Korean island and a nationwide South Korean air-raid warning event share entity/actor or semantic similarity within the discovery window
- **THEN** the pair is recalled for relationship evaluation

#### Scenario: Distinct events linked by shared primary actor despite low cosine similarity
- **WHEN** an event reporting Israeli air strikes pinned in `Gaza Strip` retains primary actor `"Israel"` and another active event reporting Israeli prisoner interrogation policy pinned in `Israel` also retains actor `"Israel"` while their embedding cosine similarity is `0.25`
- **THEN** bounded actor-mediated candidate recall still pairs both events for relationship classification

### Requirement: Structured classification with duplicate merge handoff and budget bounds
Relationship evaluation SHALL process uncached candidate pairs in bounded LLM batches within per-run call limits (passing both `WHERE` location and `WHO` actor context), persist only `CAUSED`, `FOLLOW_UP`, `REACTION`, or `RELATED` outcomes with confidence `>= 0.70`, hand off `SAME_INCIDENT` outcomes passing safety guards to `EventMergeService.merge` while removing any stale edge between the pair, cache `NONE` verdicts by pair state hash, and recompute pair hashes on `relation-v2` prompt updates.

#### Scenario: Missed duplicate detected in relationship stage triggers guarded auto-merge
- **WHEN** the relationship classifier identifies an unmerged pair of distinct active/stale event IDs as `SAME_INCIDENT` with confidence `>= 0.70` and compatible thread state
- **THEN** no relationship edge is created, any prior edge between the two events is deleted, the loser merges atomically into the deterministic survivor via `EventMergeService.merge`, and the outcome is recorded in `cluster_decisions`

#### Scenario: Unsafe SAME_INCIDENT pair still blocks fake link without forcing invalid merge
- **WHEN** a pair is classified as `SAME_INCIDENT` below the confidence threshold or fails thread/status merge safety guards
- **THEN** no relationship edge is persisted between the two events and no unsafe merge is performed

#### Scenario: Unchanged pair skipped on subsequent runs
- **WHEN** neither event's membership hash, version, actor metadata, nor prompt version has changed since the last evaluation
- **THEN** the discovery stage skips re-evaluating that pair without spending an LLM call

#### Scenario: Per-run LLM budget exhausted
- **WHEN** the worker's per-run LLM call budget is reached mid-stage
- **THEN** relationship discovery stops cleanly, preserves already-committed edges, and defers remaining pairs to the next run

### Requirement: Coexistence with story threads
Pairwise event relationships SHALL operate independently of single-parent story threads so any event can hold multiple typed connections to other events while optionally belonging to a story thread.

#### Scenario: Event participates in multiple relationships and a thread
- **WHEN** an event belongs to a story thread and also has both a `CAUSED` outgoing edge and a `REACTION` incoming edge
- **THEN** the thread assignment and both pairwise relationships remain intact and independently queryable

### Requirement: Merge-safe relationship preservation
When a duplicate event merges into a survivor event, the system SHALL remove any edge directly connecting the two merged events and repoint or deduplicate all remaining edges referencing the merged loser onto the survivor.

#### Scenario: Loser event has third-party relationships before merge
- **WHEN** event `B` merges into survivor `A` while `B` has an edge to `C`
- **THEN** any direct edge between `A` and `B` is removed, and the edge to `C` is moved to `A` unless `A` already has a relationship with `C`, in which case the duplicate edge is removed

### Requirement: Separate incident pin location (WHERE) and normalized actor retention (WHO)
The synthesis pipeline SHALL keep `Event` spatial pins fixed at the primary incident site (`WHERE`) while retaining normalized structured actors (`WHO`: `name`, `kind`, `role`, optional `location_name` and `country_code`, plus cached Nominatim-geocoded coordinates via `hermes-ai`) in `events.actors`, without creating duplicate events or `event_relationships` rows for intra-event actors.

#### Scenario: Cross-border attack pins incident location and retains external state actor
- **WHEN** `DescribeStage` synthesizes an event titled `"Israeli attacks on Gaza kill eight people including senior education official"`
- **THEN** the event's plotted pin stays at `Gaza Strip` (`PS`), its `actors` array retains `"Israel"` (`kind="STATE"`, `role="ACTOR"`, `country_code="IL"`, Nominatim-geocoded coordinates) alongside named officials, and no duplicate event row is created in Israel

#### Scenario: Actor extraction never accepts LLM-generated coordinates
- **WHEN** an event actor carries a geographic origin such as `"Israel"` or `"Russia"`
- **THEN** actor coordinates are populated solely from `hermes-ai`'s `geocode_cache` / rate-limited Nominatim `GeocodingService` and remain `null` when geocoding fails

### Requirement: Relationship and actor exposure via map and detail APIs
The API SHALL include `relationship_count` and retained `actors` on plotted map events and event summaries, return connected event summaries, rationales, and structured `actors` on event detail responses, and expose a viewport relationship endpoint returning `list[MapRelationshipEdgeResponse]` edges touching at least one visible event with both endpoints' coordinates while excluding merged or archived events and without inflating `relationship_count` with intra-event actor links.

#### Scenario: Event detail returns cross-border connection and structured actors
- **WHEN** a client requests details for the Islamabad watch-party event or the Gaza strike event
- **THEN** the detail response returns `actors` (`WHO`, including actor role and geocoded origin when external) alongside `relationships` (`CONNECTED EVENTS` with counterpart ID, headline, category color, coordinates, relationship type, direction, and rationale)

#### Scenario: Bbox map response carries cross-border actor origins separately from relationship counts
- **WHEN** a client queries `/events/bbox` for an area containing a single unlinked cross-border strike event (`1e8f326d`) pinned in `Gaza Strip` with external actor `Israel`
- **THEN** the event item reports `relationship_count: 0` while including `"Israel"` with its geocoded origin coordinates inside `actors`

#### Scenario: Viewport relationship query returns off-screen partner coordinates
- **WHEN** a client queries viewport relationships with valid `north`, `south`, `east`, and `west` bounds containing at least one connected event
- **THEN** the response includes each active `Event <-> Event` edge touching a visible event along with valid source and target coordinates, omitting edges with merged, archived, or unlocated endpoints
