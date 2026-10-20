# Proposal

## Why

Hermes currently relies strictly on XML RSS feeds for article ingestion and ranks events using a simplistic sum of source credibility tiers decayed by an arbitrary flat 10% per hour. Because major primary wire agencies (Associated Press and Reuters) have discontinued open RSS feeds, Hermes is blind to crucial breaking wires and primary reporting. Furthermore, the existing ranking treats identical syndicated wire stories as independent consensus signals, ignores coverage velocity spikes, cannot measure cross-border geopolitical diversity, and treats low-impact lifestyle stories with the same gravity as critical global crises. 

Expanding ingestion to multi-source providers (starting with GDELT 2.0 DOC API) and implementing a multi-factor ranking model ensures Hermes surfaces neutral, high-consequence global events without violating AWS ECS Fargate serverless resource boundaries.

## What Changes

- **Multi-Source Ingestion Architecture**:
  - Implement a pluggable `BaseArticleFetcher` adapter pattern in `hermes-worker`.
  - Add `GDELTFetcher` to ingest AP News (`apnews.com`), Reuters (`reuters.com`), and global wire dispatches without API keys or headless browsers.
  - Retain `RSSFetcher` for existing feeds and introduce `SitemapFetcher` (via `trafilatura`) as an on-demand fallback.
  - Update `sources` seed data to curate low-bias wire agencies and chartered public broadcasters (Reuters, AP, AFP, BBC, DW, NHK World, PBS NewsHour).
- **Multi-Factor Event Ranking Engine**:
  - **Syndication De-Biasing**: Downweight syndicated republishing of the same wire story using submodular diminishing returns.
  - **Coverage Velocity**: Incorporate time-derivative velocity multipliers to highlight sudden breaking news surges.
  - **Geopolitical Diversity Entropy**: Compute Shannon entropy across publisher countries and regions to elevate cross-border consensus on the global map.
  - **LLM Real-World Severity Triage**: Extend AI extraction schema to classify event impact (`CRITICAL`, `MAJOR`, `MODERATE`, `MINOR`) in a single inference pass.
  - **Exponential Half-Life Decay**: Replace the flat 10% hourly database decrement with continuous half-life decay ($T_{1/2} = 18\text{h}$).

## Capabilities

### New Capabilities
- `news-ingestion`: Pluggable news acquisition supporting RSS feeds, GDELT 2.0 DOC API for wire services, and fallback HTML scraping within ephemeral serverless constraints.
- `event-ranking`: Multi-factor trending score computation synthesizing source credibility, wire de-biasing, coverage velocity, geopolitical diversity entropy, severity triage, and continuous half-life decay.

### Modified Capabilities
*(None - first formal capability specs for Hermes)*

## Impact

- **Worker (`apps/hermes-worker`)**: Replaces monolithic RSS fetching in `services/rss.py` with provider adapters; updates `services/sync.py` and `services/lifecycle.py`.
- **AI Extraction (`libs/shared/hermes-ai`)**: Adds `impact_level` to `ExtractedEvent` model and updates system prompts in `utils/prompts.py`.
- **Database (`libs/shared/hermes-db`)**: Updates `sources` seed data; adds database migration for `impact_level` and `velocity` fields on `events` table; updates `EventService` scoring formulas.
- **API & Frontend (`apps/hermes-api`, `apps/hermes`, `libs/map`)**: Exposes updated trending scores and severity metadata to the map HUD without breaking existing bounding-box contracts.
