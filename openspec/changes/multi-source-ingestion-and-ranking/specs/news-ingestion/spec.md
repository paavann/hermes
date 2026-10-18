# Spec Delta

## Purpose

Enables Hermes to ingest articles across heterogeneous news providers including RSS feeds, GDELT 2.0 API queries, and sitemaps with unified normalization.

## ADDED Requirements

### Requirement: Unified Article Fetching Adapter Interface
The ingestion engine SHALL support pluggable source fetchers implementing a common interface returning normalized articles with canonical URLs, publication timestamps, and content snippets.

#### Scenario: Fetching from standard RSS feed
- **WHEN** an active source is configured with source type RSS
- **THEN** the system parses the XML feed and emits normalized articles with deduplicated URLs

#### Scenario: Fetching wire articles via GDELT 2.0
- **WHEN** an active source is configured with source type GDELT for AP News or Reuters
- **THEN** the system queries the GDELT DOC API, throttles requests to 1 per 5 seconds, and maps the JSON response into normalized articles

#### Scenario: Fallback HTML article extraction
- **WHEN** an outlet has no viable RSS or GDELT feed but publishes an XML sitemap
- **THEN** the system extracts newly discovered URLs and scrapes clean article prose using a lightweight HTML extractor without headless browsers

### Requirement: Ingestion Rate Limiting and Circuit Breaker
The ingestion engine SHALL enforce external rate limits with strict burst control and circuit breaker cooldowns when communicating with upstream news providers using an adapted token bucket limiter.

#### Scenario: Upstream request pacing with burst control
- **WHEN** communicating with rate-limited upstream providers like GDELT (1 request per 5 seconds)
- **THEN** the system uses a token bucket rate limiter configured with strict burst control (max_burst=1.0) to enforce minimum intervals between calls

#### Scenario: Provider rate limit encountered
- **WHEN** an upstream provider responds with HTTP 429 Too Many Requests or HTTP 403
- **THEN** the rate limiter trips its circuit breaker for a cooldown period, logs a warning, and skips the source until cooldown expires without crashing the worker process
