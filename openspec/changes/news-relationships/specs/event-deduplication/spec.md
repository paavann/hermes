# Spec Delta

## Purpose

Ensures near-duplicate articles and events describing the same real-world occurrence merge into a single canonical event pin even when outlets vary in entity naming, category assignment, or geographic granularity.

## ADDED Requirements

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
