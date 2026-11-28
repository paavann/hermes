# Event Deduplication Specification

## Purpose

Ensures near-duplicate articles and events describing the same real-world occurrence merge into a single canonical event pin even when outlets vary in entity naming, category assignment, or geographic granularity.

## Requirements

### Requirement: Soft entity overlap across name variants
Pairwise clustering and event reconciliation SHALL match named entities using normalized token containment and multi-token overlap in addition to exact normalized string equality.

#### Scenario: Partial person name matches full person name
- **WHEN** one report extracts entity `"Muhammad Zeeshan Ali"` and another report of the same incident extracts `"Zeeshan Ali"`
- **THEN** pairwise entity comparison recognizes a positive entity match rather than treating the entity sets as disjoint

#### Scenario: Disjoint entities remain unmatched
- **WHEN** two reports contain entities with no exact match and no meaningful multi-token containment
- **THEN** pairwise entity comparison records zero entity overlap

### Requirement: High-similarity override for disjoint entity labels
Pairwise scoring SHALL NOT apply a hard entity-disjointness veto when semantic embedding cosine similarity between the two candidates is at least `0.86`.

#### Scenario: High semantic similarity bypasses entity veto
- **WHEN** two reports describe the same occurrence with cosine similarity `>= 0.86` while extracting differently phrased entity names such as `"Tiangong"` and `"China's space station"`
- **THEN** the pair is NOT vetoed on entities and proceeds to weighted scoring and adjudication

#### Scenario: Low semantic similarity preserves entity veto
- **WHEN** two reports have disjoint entity sets and cosine similarity `< 0.86`
- **THEN** the pair remains vetoed as separate incidents

### Requirement: Same-country broad-scope location compatibility
Event merge scoring SHALL treat two events in the same country as location-compatible when at least one event has `COUNTRY` or `GLOBAL` geographic scope, while preserving the `100 km` distance veto when both events have `CITY` or `LOCAL` scope.

#### Scenario: Country-centroid event reconciles with city-level event
- **WHEN** one duplicate event is geocoded to a country centroid with `COUNTRY` scope and another is geocoded to a specific city in the same country over `100 km` away
- **THEN** merge scoring treats their locations as compatible rather than vetoing on distance

#### Scenario: Distant local incidents in the same country stay separate
- **WHEN** two `CITY`- or `LOCAL`-scope events in the same country are more than `100 km` apart
- **THEN** merge scoring vetoes the pair on location

### Requirement: Syndication-neutral merge scoring and gray-band adjudication
Duplicate event merge scoring SHALL compute its base score up to `1.0` without penalizing pairs that share zero syndication families, apply shared families only as an additive bonus capped at `1.0`, and route pairs scoring at least `0.74` to LLM duplicate adjudication.

#### Scenario: Independent outlets with differing categories reach adjudication
- **WHEN** two single-source events from different syndication families report the same spaceflight incident under `SCIENCE` and `TECHNOLOGY`
- **THEN** the pair is not capped below merge eligibility by missing family overlap and reaches duplicate adjudication

#### Scenario: Confirmed duplicate events collapse into survivor
- **WHEN** duplicate adjudication determines two events describe the exact same real-world occurrence
- **THEN** the system merges the loser into the survivor and preserves a merge redirect without deleting historical evidence

### Requirement: Reconciliation ordering and 48-hour merge window
The event-building pipeline SHALL evaluate candidate duplicate event pairs across at least a `48`-hour activity window and complete duplicate reconciliation before pairwise relationship discovery begins.

#### Scenario: Late follow-up duplicate within 48 hours merges before linking
- **WHEN** a duplicate event pin was updated `36` hours after the original event pin
- **THEN** reconciliation evaluates and merges the duplicate before relationship analysis runs on active events

### Requirement: Dedicated event-to-event merge adjudication
Event reconciliation SHALL evaluate gray-band event pairs using a dedicated event-merge adjudication prompt (`merge-v1`) rather than the article-to-event ingestion clustering prompt (`adjudicate-v1`), incorporating retained actors alongside locations and timestamps so multi-outlet coverage of the same official release or single milestone transition merges cleanly without collapsing distinct cross-border reactions.

#### Scenario: Same statistical release with differing secondary entities merges
- **WHEN** two active UK politics events report the same provisional `77,000` ONS net migration figure for the year ending June 2026 while citing different secondary entities such as `"Home Office"` vs `"Liberal Democrats"`
- **THEN** event-merge adjudication classifies the pair as `SAME` and collapses them into one canonical event pin

#### Scenario: Scheduled announcement and execution of the same milestone merge
- **WHEN** one event reports that astronaut `Muhammad Zeeshan Ali` is set to board China's Tiangong space station launching Wednesday and a second event reports that `Zeeshan Ali` boarded China's space station
- **THEN** event-merge adjudication classifies the two China event cards as `SAME` and merges them into one canonical China event pin

#### Scenario: Distinct regional reaction event stays separate during merge check
- **WHEN** the China Tiangong boarding event is compared against an Islamabad SUPARCO watch-party event involving crowds in Pakistan
- **THEN** event-merge adjudication classifies the pair as `DIFFERENT` so both distinct geographic events remain plotted and available for relationship linking

### Requirement: Structured actor inclusion and prompt-version cache isolation
Pair reconciliation SHALL include retained event actors when computing entity similarity and SHALL isolate merge adjudication decisions under a versioned event-merge key so prior `adjudicate-v1` `DIFFERENT` rejections do not block re-evaluation under `merge-v1`.

#### Scenario: Event whose source articles lacked label entities reconciles via event actors
- **WHEN** an older event has empty `article_labels.entities` while carrying retained `Event.actors`
- **THEN** pair reconciliation uses the retained actors for candidate similarity and LLM merge adjudication instead of treating the event as entity-empty

#### Scenario: Prompt version bump re-evaluates previously rejected duplicate pair
- **WHEN** a pair previously received a cached `DIFFERENT` verdict under `adjudicate-v1` and reconciliation runs after upgrading to `merge-v1`
- **THEN** the pair hash misses the old cache entry and re-evaluates cleanly under `merge-v1`
