# Design

## Context

`hermes-worker` operates as an ephemeral batch task on AWS ECS Fargate (`0.25 vCPU`, `512 MiB` RAM), triggered 3x daily. Ingestion must stay within this constrained memory and runtime envelope without spinning up headless browser runtimes. The system relies on PostGIS for spatial geometries and pgvector (`halfvec(2048)`) for deduplication. See `proposal.md` for motivation and `specs/` for behavioral requirements.

## Goals / Non-Goals

**Goals:**
- Provide a unified, pluggable ingestion adapter interface (`BaseArticleFetcher`) supporting RSS, GDELT 2.0 API, and sitemap/HTML fallback.
- Ingest primary wire services (AP News, Reuters) via GDELT 2.0 DOC API JSON without API keys or browser automation.
- Re-use and extend the existing `TbRateLimiter` in `hermes-ai` with burst control (`max_burst=1.0`) and circuit-breaking.
- Implement an unbiased, multi-factor ranking formula combining primary source authority, syndication de-biasing, coverage velocity, cross-bloc Shannon diversity entropy across 5 geopolitical regions, and LLM severity triage.
- Replace arbitrary flat 10% decrements with smooth continuous exponential half-life decay ($T_{1/2} = 18\text{h}$).

**Non-Goals:**
- Running persistent browser daemons (Playwright / Puppeteer / Selenium) inside Fargate containers.
- Scraping or managing independent news feeds for dozens or hundreds of individual countries (GDELT and ~10 curated global sources provide the cross-bloc coverage).
- Switching from ephemeral 12-factor batch execution to persistent WebSocket streaming daemons.
- Overhauling the core vector embedding (`nemotron-3-embed-1b`) or PostGIS spatial storage models.

## Decisions

### 1. Ingestion Adapter Architecture & `TbRateLimiter` Extension
- **Decision**: Define an abstract protocol `BaseArticleFetcher` with a standardized async method `fetch_articles(source: DueSource) -> list[ParsedArticle]`. Concrete implementations:
  - `RSSFetcher`: Uses `httpx` + `feedparser` (current functionality).
  - `GDELTFetcher`: Queries `https://api.gdeltproject.org/api/v2/doc/doc` with domain filters and strict 5-second pacing.
  - `SitemapFetcher`: Extracts URLs from XML sitemaps and parses text with `trafilatura`.
- **Rate Limiting & Circuit Breaker**: Extend the existing `TbRateLimiter` in `libs/shared/hermes-ai/src/hermes_ai/utils/rate_limiter.py` by adding:
  - `max_burst: float | None = None`: When set to `1.0` (with `req_per_min=12`), strictly caps bucket capacity to 1 token, guaranteeing an exact 5.0-second delay between GDELT requests without initial bursting.
  - `circuit_cooldown_seconds: float = 120.0` with `trip_circuit_breaker()` and `is_circuit_open()`: Trips when upstream responds with HTTP 429/403, failing fast and preventing IP blacklists.
- **Alternatives Considered**: Direct headless browser scraping (rejected due to Fargate 512 MiB RAM boundary and Cloudflare IP blocks); third-party rate-limiting packages (rejected to adhere to DRY and maintain full control over async locks).

### 2. Shannon Diversity Entropy Across 5 Geopolitical Blocs
- **Decision**: Rather than attempting to ingest feeds from 195 separate countries, map all reporting outlets (from GDELT's `sourcecountry` and our curated sources) into 5 coarse-grained geopolitical blocs:
  1. `NORTH_AMERICA` (United States, Canada)
  2. `EUROPE` (United Kingdom, Germany, France, etc.)
  3. `ASIA_PACIFIC` (Japan, India, Australia, etc.)
  4. `MIDDLE_EAST_AFRICA` (Qatar, UAE, South Africa, etc.)
  5. `LATIN_AMERICA` (Brazil, Mexico, etc.)
  6. `GLOBAL_WIRE` (Reuters, Associated Press, AFP)
- **Entropy Calculation**: Measure geographic publisher dispersion using Shannon Information Entropy over the reporting blocs:
  $$H = -\sum_{i=1}^{K} p_i \ln(p_i)$$
  where $p_i$ is the proportion of reporting outlets belonging to bloc $i$. The diversity multiplier is $D = 1.0 + \min(H, 1.0) \times 0.5$.
- **Rationale**: An event covered only by 3 US outlets yields $H=0$ ($D=1.0$). An event corroborated by Reuters (`GLOBAL_WIRE`), BBC (`EUROPE`), and Al Jazeera (`MIDDLE_EAST_AFRICA`) yields high entropy ($D \approx 1.5$), boosting cross-border global consensus on the map without requiring dozens of foreign scrapers.

### 3. Submodular Diminishing Returns for Syndicated Wires
- **Decision**: When multiple articles for an event originate from the same news agency wire (e.g. AP or Reuters syndication), the added credibility score for the $n$-th syndicated article is weighted by $\frac{1}{\sqrt{n}}$.
- **Rationale**: Prevents regional newspapers republishing the same syndicated wire copy from artificially inflating an event's trending score.

### 4. Zero-Overhead Severity Triage in LLM Extraction
- **Decision**: Add `impact_level: Literal["CRITICAL", "MAJOR", "MODERATE", "MINOR"]` to the existing `ExtractedEvent` Pydantic model in `hermes-ai`.
- **Rationale**: Evaluated during the single existing batch LLM extraction pass (`ARTICLE_SYSTEM_PROMPT`). Adds zero additional network roundtrips or token overhead.

### 5. Continuous Exponential Half-Life Decay
- **Decision**: Update lifecycle transition in `EventService` to apply:
  $$\text{Score}(t) = \text{Score}_0 \cdot 2^{-\frac{\Delta t}{18}}$$
  where $\Delta t$ is elapsed hours since last reported article.
- **Rationale**: Replaces discontinuous, step-like flat 10% decrements with smooth physics-based decay.

## Risks / Trade-offs

- **[GDELT Rate Limit]** GDELT returns 429 if called faster than once per 5 seconds.
  → *Mitigation*: Handled by `TbRateLimiter(req_per_min=12, max_burst=1.0)` which strictly enforces 5.0s between calls, backed by `trip_circuit_breaker()`.
- **[HTML Scraping Anti-Bot Challenges]** Some sitemaps may block AWS datacenter IPs.
  → *Mitigation*: `SitemapFetcher` is an optional fallback; if a fetch fails with 403/Captcha, the source logs a warning and skips cleanly without halting the worker.
- **[LLM Severity Inconsistency]** LLMs may occasionally over-classify regional events as critical.
  → *Mitigation*: Strict enum constraint in Pydantic schema with concrete guidelines in `ARTICLE_SYSTEM_PROMPT`.

## Migration Plan

1. **Database Schema**: Add Alembic migration to add `impact_level` (String/Enum) and `velocity` (Float) columns to the `events` table in `libs/shared/hermes-db`.
2. **Seed Data**: Update `libs/shared/hermes-db/src/hermes_db/data/sources.json` to include GDELT wire sources (AP, Reuters, AFP) and public broadcasters with appropriate `SourceType`.
3. **Rollback Strategy**: The database migration columns have default values, making the change backward-compatible with older worker versions.
