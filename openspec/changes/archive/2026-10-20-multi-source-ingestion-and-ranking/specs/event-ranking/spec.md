# Spec Delta

## Purpose

Calculates dynamic, unbiased trending scores for geospatial events by synthesizing source authority, coverage velocity, cross-border diversity, severity, and continuous decay.

## ADDED Requirements

### Requirement: Multi-Factor Trending Score Calculation
The event service SHALL compute an event trending score using source credibility, diminished returns for syndicated copies, coverage velocity, and geographic diversity entropy.

#### Scenario: Syndicated wire copy deduplication
- **WHEN** an event is matched with multiple articles originating from the same news agency wire
- **THEN** additional matching articles receive submodular diminishing weight rather than full tier increments

#### Scenario: Cross-border consensus amplification
- **WHEN** an event is corroborated by publishers spanning multiple distinct geopolitical blocs (North America, Europe, Asia-Pacific, Latin America, Middle East/Africa)
- **THEN** the system calculates Shannon diversity entropy over reporting blocs and applies an informational diversity multiplier greater than 1.0 to the base score

#### Scenario: Breaking velocity boost
- **WHEN** an event experiences a rapid cluster of incoming reports within a short time window
- **THEN** the system calculates a positive velocity multiplier that elevates the event's prominence

### Requirement: Real-World Severity Classification
The AI extraction pipeline SHALL triage every new incident and assign a standardized severity tier that scales the event's initial trending score.

#### Scenario: Critical global crisis classification
- **WHEN** an incoming article details armed conflict, major natural disaster, or sovereign governance collapse
- **THEN** the AI extractor outputs an impact tier of CRITICAL with a high base severity multiplier

#### Scenario: Routine or lifestyle story classification
- **WHEN** an incoming article covers entertainment, celebrity updates, sports, or localized municipal affairs
- **THEN** the AI extractor outputs an impact tier of MINOR with a baseline severity multiplier

### Requirement: Continuous Half-Life Decay
The event lifecycle engine SHALL decay active event scores according to an exponential half-life decay function based on elapsed time since the last reported article.

#### Scenario: Lifecycle score decay execution
- **WHEN** the lifecycle background transition job executes
- **THEN** active event scores decay continuously as a function of elapsed hours using an 18-hour half-life curve
