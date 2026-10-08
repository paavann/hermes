# Hermes API — AI Agent Context

## 1. Application Role & Boundaries
This is the **stateless backend REST API and on-demand timeline synthesis engine**.
- **12-Factor Compliance**: `hermes-api` executes **zero background schedulers or ingestion workers**. All autonomous RSS harvesting and lifecycle decay happen in `hermes-worker`. This decoupling prevents event loop starvation and task duplication across API replicas.
- **Data Layer Boundary**: Database models and migrations are externalized to `libs/shared/hermes-db`. Do not define ORM models here.

## 2. Timeline Engine Orchestration Flow
The `/events/tl` endpoint orchestrates a complex, non-obvious pipeline:
1. **Triage**: Asks LLM if the event warrants a timeline (rejects routine news).
2. **Extraction**: Interrogates MediaWiki, detecting multi-year index pages and batching extracts.
3. **Graphing**: LLM extracts nodes (historical milestones) and edges (causal verbs).
4. **Grounded Geocoding**: Resolves exact coordinates for historical nodes to prevent hallucination.
5. **Terminal Stitching**: Injects the active breaking event as the final `"current-event"` node.

## 3. CORS Error Handling Caveat
`hermes-api` features a custom exception handler registry (`core/errors.py`). To prevent FastAPI exception responses from bypassing the outer `CORSMiddleware` (which causes opaque browser CORS errors), custom error handlers manually inject the `Access-Control-Allow-Origin` header via the `_cors_headers()` utility. Maintain this pattern for any new exception handlers.