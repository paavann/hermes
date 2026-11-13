# Chat Map Integration Specification

## Purpose

Keeps the conversation and the map visible together, and turns citations into a navigable index of the plotted evidence behind each answer.

## Requirements

### Requirement: Simultaneous chat and map visibility

The chat interface SHALL render as a dismissible overlay while the map remains full-bleed, visible, and interactive; opening or closing chat MUST NOT require a page navigation or destroy map state.

#### Scenario: Chat open with map visible
- **WHEN** the chat panel is open
- **THEN** the map remains visible and accepts pan, zoom, and pin selection alongside the conversation

#### Scenario: Chat closed and reopened
- **WHEN** the user closes and reopens the chat panel
- **THEN** the current conversation and map viewport are preserved

### Requirement: Citation-driven map focus

Activating an event, article, or timeline citation SHALL focus the map on the associated plotted event and open its detail popup.

#### Scenario: Event citation activated
- **WHEN** the user activates an `[E#]` citation
- **THEN** the map flies to that event and opens its detail popup

#### Scenario: Article or timeline citation activated
- **WHEN** the user activates an `[A#]` or `[T#]` citation
- **THEN** the map focuses the parent event and opens its detail popup

#### Scenario: Web citation activated
- **WHEN** the user activates a `[W#]` citation
- **THEN** the external source opens in a new browser context and the map does not move

### Requirement: Persistent cited-pin highlighting

While an answer is displayed, every plotted event cited by that answer SHALL be persistently highlighted on the map; highlights SHALL be replaced by the next answer and cleared when chat closes.

#### Scenario: Multiple cited pins
- **WHEN** an answer cites three plotted events
- **THEN** all three pins remain highlighted while that answer is visible

#### Scenario: Next answer replaces highlights
- **WHEN** a new answer cites a different set of events
- **THEN** the previous highlights are cleared and the new cited pins are highlighted

#### Scenario: Closing chat clears highlights
- **WHEN** the chat panel is closed
- **THEN** all citation-driven pin highlights are removed

### Requirement: Scope defaults from map state

The chat scope SHALL default to the selected event when one is open, otherwise the current viewport, otherwise global plottings; an explicit user choice SHALL persist for the session and override map-derived defaults.

#### Scenario: Selected event determines scope
- **WHEN** an event popup is open and the user has not chosen a scope
- **THEN** chat requests use that event's scope

#### Scenario: Viewport determines scope
- **WHEN** no event is selected and the map has a viewport
- **THEN** chat requests use the viewport scope

#### Scenario: Global fallback
- **WHEN** no event is selected and no viewport is available
- **THEN** chat requests use the global scope

#### Scenario: User override persists
- **WHEN** the user explicitly selects a scope
- **THEN** later map selections and pans do not change that choice for the session

### Requirement: Visual distinction of evidence types

External web citations and background knowledge SHALL be visually distinguished from plotted evidence, and the answer footer SHALL report counts of plotted, web, and background evidence.

#### Scenario: Web evidence displayed
- **WHEN** an answer includes a `[W#]` citation
- **THEN** it is styled as external evidence and shows its source and publication time

#### Scenario: Background knowledge displayed
- **WHEN** an answer includes a `[BG]` marker
- **THEN** that content is styled as unverified background rather than plotted evidence

#### Scenario: Grounding footer
- **WHEN** an answer completes
- **THEN** the footer reports how many plotted, web, and background sources contributed

### Requirement: Recoverable streaming failure

When the answer stream fails, the panel SHALL show an actionable error and a retry affordance, and the map and previously completed messages SHALL remain usable.

#### Scenario: Stream error mid-answer
- **WHEN** the stream emits an error after partial tokens
- **THEN** the partial answer is marked incomplete and a retry control is shown

#### Scenario: Retry after failure
- **WHEN** the user activates retry
- **THEN** the same turn is submitted again without losing earlier conversation turns

### Requirement: No autonomous map control

The assistant SHALL NOT autonomously change the map camera, filters, scope, or layers in this phase; only user citation activation and explicit scope controls may change map state.

#### Scenario: Model suggests a map action
- **WHEN** answer text suggests zooming or filtering the map
- **THEN** the map does not change until the user performs the action manually
