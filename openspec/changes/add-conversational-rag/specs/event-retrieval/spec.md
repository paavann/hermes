# Spec Delta

## Purpose

Selects the plotted events, articles, and timeline context that ground each conversational turn, using both lexical and semantic relevance within the user's current map scope.

## ADDED Requirements

### Requirement: Hybrid lexical and semantic retrieval

The retrieval service SHALL rank candidate events using both full-text lexical matching and semantic vector similarity, fuse the two rankings without comparing their raw scores, and return a single ordered result set.

#### Scenario: Named-entity query
- **WHEN** the user asks about a specific place, person, or organization named in event text
- **THEN** events containing those terms appear in the lexical ranking and in the fused result set

#### Scenario: Conceptual query
- **WHEN** the user asks a conceptual question that shares few keywords with event text
- **THEN** semantically related events appear in the fused result set through vector similarity

#### Scenario: Agreement across methods
- **WHEN** an event ranks highly in both lexical and semantic results
- **THEN** it appears above events that rank highly in only one method

### Requirement: Scope resolution

The retrieval service SHALL resolve scope in priority order: an explicitly selected event, then the current map viewport, then all eligible plottings.

#### Scenario: Selected event scope
- **WHEN** an event is selected on the map and no scope override is supplied
- **THEN** retrieval returns that event together with its linked articles and timeline

#### Scenario: Viewport scope
- **WHEN** no event is selected and the map has a viewport
- **THEN** retrieval returns eligible events whose coordinates fall inside that viewport

#### Scenario: Global scope
- **WHEN** no event is selected and no viewport is available
- **THEN** retrieval searches all eligible plottings

### Requirement: Eligibility window

Only `ACTIVE` and `STALE` events whose last update falls within the seven-day lookback SHALL be retrievable; `ARCHIVED` events MUST be excluded, and `STALE` events SHALL expose their age to the answer layer.

#### Scenario: Active and stale events included
- **WHEN** eligible events are `ACTIVE` or `STALE` and within the lookback
- **THEN** they may appear in retrieval results

#### Scenario: Archived events excluded
- **WHEN** an event is `ARCHIVED`
- **THEN** it never appears in retrieval results regardless of relevance

#### Scenario: Stale age exposed
- **WHEN** a `STALE` event is retrieved
- **THEN** its result includes how long it has been since the last update

### Requirement: Bounded recency and trending boosts

After rank fusion, the service SHALL apply bounded recency and trending-score boosts that refine ordering without allowing a weakly relevant event to outrank a strongly relevant one.

#### Scenario: Near-equal relevance favors fresher event
- **WHEN** two events have comparable fused relevance but one is newer or trending higher
- **THEN** the newer or trending event ranks first

#### Scenario: Boost cannot override relevance
- **WHEN** an event has very weak relevance but a high trending score
- **THEN** it does not outrank a strongly relevant event

### Requirement: Complete retrieval context

Each retrieved event SHALL include its headline, summary, category, impact level, location, timestamps, linked article titles with URLs and source names, and any generated timeline nodes, edges, and summary.

#### Scenario: Answer context includes linked reporting
- **WHEN** a retrieved event has linked articles and a generated timeline
- **THEN** the answer context contains the article references and timeline content alongside the event summary

#### Scenario: Event without timeline
- **WHEN** a retrieved event has no generated timeline
- **THEN** the event is still returned with its other available context

### Requirement: Coverage signal for web escalation

The result SHALL include a coverage signal describing whether local evidence is empty, thin, or sufficient, so the chat layer can decide whether to escalate to external search.

#### Scenario: No local matches
- **WHEN** no eligible event matches the query
- **THEN** the result reports empty coverage

#### Scenario: Thin local matches
- **WHEN** only one weak or stale event matches the query
- **THEN** the result reports thin coverage

#### Scenario: Sufficient local matches
- **WHEN** multiple relevant and sufficiently fresh events match the query
- **THEN** the result reports sufficient coverage

### Requirement: Planner-supplied filters

Category, time-range, and geographic filters produced by the planner SHALL be applied before ranking and SHALL narrow the candidate set without bypassing the eligibility window.

#### Scenario: Category filter applied
- **WHEN** the planner supplies a category filter
- **THEN** only events in that category are ranked and returned

#### Scenario: Filter cannot revive archived events
- **WHEN** a filter would match an `ARCHIVED` or out-of-window event
- **THEN** that event remains excluded
