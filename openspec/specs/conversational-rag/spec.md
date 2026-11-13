# Conversational RAG Specification

## Purpose

Provides a grounded conversational interface over Hermes plottings that answers user questions with traceable evidence, explicit background labeling, and bounded external web search.

## Requirements

### Requirement: Streaming chat endpoint

The system SHALL expose `POST /api/v1/chat` as a stateless Server-Sent Events stream that accepts a user message, client-held conversation history, and a retrieval scope, and emits ordered `status`, `token`, `sources`, `done`, and `error` events.

#### Scenario: Successful streamed answer
- **WHEN** a client posts a valid message with history and scope
- **THEN** the response is `text/event-stream` and emits at least one `status`, one or more `token`, exactly one `sources`, and exactly one terminal `done` event, in that order

#### Scenario: Invalid request rejected before streaming
- **WHEN** a request omits the message or supplies a malformed scope
- **THEN** the system returns an HTTP 422 validation error without opening an event stream

#### Scenario: Failure after streaming begins
- **WHEN** the answer model fails after at least one token has been emitted
- **THEN** the stream emits a terminal `error` event and does not restart the answer

### Requirement: Citation-bearing current-affairs claims

Every current-affairs claim in an answer SHALL carry an inline citation to a retrieved event `[E#]`, article `[A#]`, timeline node `[T#]`, or web result `[W#]`; claims without supporting evidence MUST NOT be presented as fact.

#### Scenario: Answer grounded in plotted evidence
- **WHEN** the retrieved local evidence supports the answer
- **THEN** each factual claim cites at least one plotted event, article, or timeline identifier

#### Scenario: Unsupported claim refused
- **WHEN** neither local evidence nor web evidence supports a requested current-affairs claim
- **THEN** the answer states that the plottings and web search do not establish the claim instead of asserting it

### Requirement: Explicit background knowledge labeling

The system SHALL mark general knowledge that is not derived from retrieved evidence with an inline `[BG]` marker and SHALL report that background knowledge was used in the response provenance summary.

#### Scenario: Definition answered from background
- **WHEN** the user asks for a general definition not present in the plottings or web results
- **THEN** the answer prefixes that content with `[BG]` and the provenance summary reports `background: true`

#### Scenario: Background not used
- **WHEN** the answer relies only on retrieved local or web evidence
- **THEN** the provenance summary reports `background: false`

### Requirement: Bounded web search escalation

The system SHALL perform at most one external web search per turn and SHALL invoke it only when the planner requests it, local coverage is insufficient, or the question requires information newer than the retrieved plottings.

#### Scenario: Recency question triggers web search
- **WHEN** the user asks for the latest development and the newest local evidence is older than the configured freshness window
- **THEN** the system performs one web search and labels each returned item `[W#]` with its source and publication time

#### Scenario: Sufficient local evidence skips web search
- **WHEN** local evidence fully answers the question and satisfies its freshness requirement
- **THEN** the system performs no web search for that turn

#### Scenario: Web search unavailable
- **WHEN** the web search service fails or is not configured
- **THEN** the answer proceeds with local and background evidence and states that external search was unavailable

### Requirement: External evidence disclosure

Web results SHALL be presented as evidence outside the plottings, with source name, publication time, and URL, and any conflict between web and local evidence MUST be stated explicitly.

#### Scenario: Web result used in answer
- **WHEN** a web result contributes to the answer
- **THEN** the citation identifies it as external and shows its publication time

#### Scenario: Conflicting reports
- **WHEN** a web result contradicts a plotted event or article
- **THEN** the answer describes both positions and attributes each to its source rather than choosing one silently

### Requirement: Planner-driven retrieval query

Each turn SHALL begin with one structured planning step that rewrites the user message and recent history into a standalone retrieval query, optional filters, and a web-search decision, so follow-up questions remain interpretable without the prior conversation.

#### Scenario: Follow-up resolved into standalone query
- **WHEN** the user asks a follow-up that refers to an earlier subject by pronoun
- **THEN** the planner produces a standalone query naming the intended subject and retrieval uses that query

#### Scenario: Planner failure falls back safely
- **WHEN** the planning model fails or returns invalid structured output
- **THEN** the system uses the raw user message as the retrieval query and applies the current scope

### Requirement: Citation validation and provenance

Before completing a response, the system SHALL validate every emitted citation against the retrieved source set, remove or flag identifiers that do not exist, and emit a machine-readable provenance summary containing local, web, and background counts.

#### Scenario: Valid citations preserved
- **WHEN** the answer cites identifiers present in the retrieved sources
- **THEN** the `sources` event contains exactly those source records and the terminal `done` event reports their counts

#### Scenario: Unknown citation rejected
- **WHEN** the answer contains a citation identifier that was not retrieved
- **THEN** the system removes that identifier from the visible answer and does not include it in the source list

### Requirement: Stateless bounded conversation history

The server SHALL treat conversation history as client-supplied, use at most the last eight turns, and SHALL NOT persist messages or threads between requests.

#### Scenario: History supplies context
- **WHEN** a client includes prior user and assistant turns
- **THEN** the planner and answer chain use the most recent eight turns as context

#### Scenario: History exceeds limit
- **WHEN** a client supplies more than eight turns
- **THEN** the system discards older turns before planning

#### Scenario: No server-side persistence
- **WHEN** a request completes
- **THEN** no message content is written to the database or to a conversation store

### Requirement: Request rate limits and daily budget

The chat endpoint SHALL enforce a per-client-IP request rate limit and a daily token or cost budget, and MUST reject new turns once either limit is exhausted.

#### Scenario: Per-IP limit exceeded
- **WHEN** a client exceeds the configured requests-per-window limit
- **THEN** the system responds with HTTP 429 and a retry hint without invoking the planner or answer model

#### Scenario: Daily budget exhausted
- **WHEN** the daily token or cost budget has been consumed
- **THEN** the system rejects new chat turns with HTTP 429 and a budget-exhausted error code until the budget resets

### Requirement: Untrusted web content isolation

Web search snippets SHALL be treated as untrusted data: the system MUST cap their length, validate result URLs, strip instruction-like content, and MUST NOT allow snippet text to alter system instructions or tool behavior.

#### Scenario: Snippet contains injected instructions
- **WHEN** a web snippet contains text instructing the assistant to ignore its rules or reveal secrets
- **THEN** the system treats the text as evidence only and does not follow the instruction

#### Scenario: Invalid result URL
- **WHEN** a web result has a non-HTTP(S) or malformed URL
- **THEN** the system excludes it from citations and from the answer context

### Requirement: Privacy-preserving observability

When tracing is enabled, the system SHALL record chain, retrieval, and model metadata such as latency, token usage, and source counts, and MUST NOT record user messages, assistant answer text, or retrieved content.

#### Scenario: Trace excludes message content
- **WHEN** a chat turn is traced
- **THEN** the trace contains timing and usage metadata but no message, prompt, answer, or snippet text
