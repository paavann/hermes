# Tasks

## 1. Database Schema & Source Curation

- [x] 1.1 Create Alembic migration adding `impact_level` and `velocity` to `events` table in `libs/shared/hermes-db` and verify schema upgrades cleanly
- [x] 1.2 Update `libs/shared/hermes-db/src/hermes_db/data/sources.json` with GDELT wire sources (AP, Reuters, AFP) and chartered public broadcasters, and verify source model tests pass

## 2. Ingestion Adapter Engine

- [x] 2.1 Extend `TbRateLimiter` in `libs/shared/hermes-ai` with `max_burst` control and circuit breaking, and implement `BaseArticleFetcher`, `RSSFetcher`, and `GDELTFetcher` in `apps/hermes-worker` using `TbRateLimiter(req_per_min=12, max_burst=1.0)`. Verify unit tests pass with mocked GDELT JSON
- [x] 2.2 Implement optional `SitemapFetcher` fallback using `trafilatura` and verify article text extraction unit tests pass
- [x] 2.3 Refactor `SyncService` in `apps/hermes-worker` to dispatch fetching dynamically based on `source.source_type`, and verify sync pipeline tests pass

## 3. Multi-Factor Ranking & AI Triage

- [x] 3.1 Update `ExtractedEvent` schema and `ARTICLE_SYSTEM_PROMPT` in `libs/shared/hermes-ai` to classify event `impact_level`, and verify AI extraction tests pass
- [x] 3.2 Implement syndication diminishing returns, coverage velocity calculation, and Shannon geopolitical bloc diversity entropy scoring in `libs/shared/hermes-db/src/hermes_db/services/event.py`, and verify ranking score unit tests pass
- [x] 3.3 Implement continuous exponential half-life decay ($T_{1/2} = 18\text{h}$) in `run_lifecycle_transitions()`, and verify lifecycle transition tests pass

## 4. Verification & Validation

- [x] 4.1 Execute `npx nx test hermes-worker`, `npx nx test hermes-ai`, and `npx nx test hermes-db` and verify all tests pass
- [x] 4.2 Execute `npx nx lint hermes-worker`, `npx nx lint hermes-ai`, and `npx nx lint hermes-db` and verify zero lint violations
