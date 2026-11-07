# Proposal

## Why

Hermes plots events on a world map but gives users no way to interrogate them. Understanding a story means opening pins one by one, and the plotted record is intentionally shallow: `events.embedding` is built from the first article for deduplication, article bodies are discarded after ingestion, and event summaries are only a few sentences. A conversational surface grounded in the plottings turns the map into an explainable intelligence tool: users can ask what is happening, why it matters, and how a story developed, with every claim traceable back to a pin, an article, or an explicitly labeled external source.

Without a grounding contract, a chat assistant would be less trustworthy than the map itself. The answer pipeline must prefer local evidence, label external web evidence and model background separately, and refuse to present speculation as fact.

## What Changes

### Conversational interface

- Add a new frontend library `libs/chat` (`@hermes/chat`) owning the chat store, streaming client, hooks, and UI widgets. `libs/map` owns only map behavior; `apps/hermes` remains the composition root.
- Add a left-side HUD chat overlay so the map stays full-bleed and visible alongside the conversation. The existing `TlPanel` remains on the right.
- Add `POST /api/v1/chat` as a stateless Server-Sent Events stream with `status`, `token`, `sources`, `done`, and `error` events. Conversation history is client-held (last 8 turns); no thread tables, auth, or persistence in this phase.

### Grounded answer pipeline

- Build the chain with LangChain in `hermes-ai`: a `ChatPromptTemplate` + planner chain, a custom `BaseRetriever` over hybrid local search, a `TavilySearch` web tool, and a streaming answer chain. The existing LiteLLM Router remains the transport, failover, and rate-limit layer.
- Add two model groups to the shared router: `chat` for the stronger answer model and `plan` for the cheaper planner, each with its own optional fallback. Configuration gains `CHAT_MODEL`/`CHAT_API`, `PLAN_MODEL`/`PLAN_API`, their `_1` fallbacks, and `TAVILY_API_KEY`.
- Add an evidence-first answer contract: `[E#]` events, `[A#]` articles, `[T#]` timeline nodes, `[W#]` web results, and `[BG]` explicitly unverified background knowledge. Every current-affairs claim must carry a citation; web evidence is timestamped and visibly marked as outside the plottings; conflicts between local and web evidence are surfaced.
- Add citation validation and a machine-readable provenance summary (`local`, `web`, `background`, usage) so the UI can render a grounding footer and later evaluations can score groundedness.

### Local retrieval

- Add a hybrid retrieval service in `hermes-db` combining Postgres full-text search with the existing pgvector index, fused by reciprocal rank fusion, with small recency and trending boosts. The existing dedup embedding is reused as-is; no re-embedding and no new vector column.
- Resolve scope as selected event → viewport → global plottings. Retrieve `ACTIVE` and `STALE` events within a 7-day lookback and exclude `ARCHIVED`. Include article titles/URLs/sources and generated timeline nodes/edges/summary in the answer context.
- Add one GIN full-text index migration over the event search text. This is the only schema change in this phase.

### Web fallback, safety, and operations

- Add a Tavily-backed `WebSearchService` abstraction in `hermes-ai`; allow at most one search per turn, gated by the planner, low local coverage, or recency intent. Treat web snippets as untrusted: cap length, strip instruction-like content, validate URLs, and never concatenate them raw into the system prompt.
- Add per-IP rate limiting and a daily token/cost budget. Keep the API stateless and single-worker compatible.
- Trace chain, retrieval, and model calls with the existing Langfuse integration via `CallbackHandler`, while masking prompt and message content.

### Deferred

- Article body storage, chunking, and chunk-level embeddings (Phase 2).
- Persisted conversation threads, authentication on chat endpoints, rerankers, and multi-hop agent planning.
- Assistant-driven map actions such as filtering or zooming through structured model output (Phase 2/3). Phase 1 stops at clickable citations and highlighted cited pins.

## Capabilities

### New Capabilities

- `conversational-rag`: End-to-end grounded chat behavior, including the streaming API contract, planner-driven scope and web decisions, evidence labeling, citation validation, provenance reporting, conversation history, and request budgets.
- `event-retrieval`: Hybrid local retrieval and scope resolution over plotted events, articles, and timelines, including status filtering, lookback, rank fusion, and recency/trending boosts.
- `chat-map-integration`: Coexistent chat and map UI, citation-driven map focus, persistent highlighting of cited pins, and scope defaults derived from the current map state.

### Modified Capabilities

- None. Existing `event-ranking` and `news-ingestion` requirements are unchanged; chat consumes their outputs without altering ingestion or scoring behavior.

## Impact

- **`libs/shared/hermes-ai`**: New chat models, prompts, chain/retriever/tool services, Tavily client, and configuration fields. Adds `langchain-core`, `langchain-litellm>=0.11.2`, and `langchain-tavily`; the resolver upgrades `litellm` from 1.103.2 to 1.108.1 with the `[mcp]` extra. Chat imports must stay lazy so the worker does not import LangChain/LangGraph at startup.
- **`libs/shared/hermes-db`**: New `services/search.py` for hybrid retrieval and one Alembic migration adding the GIN full-text index.
- **`apps/hermes-api`**: New `/api/v1/chat` SSE route, request/response schemas, `ChatService` orchestration, chat model settings, and per-IP/budget guards.
- **`libs/chat`** (new): Chat store, SSE client, hooks, message list, citation chips, scope selector, and panel UI.
- **`libs/map`**: Only `focusEvent`/`focusTarget` store state and a cited-pin highlight layer. No chat logic enters the map library.
- **`libs/shared/util-types`**: Hand-mirrored chat request, SSE event, source, and provenance types, updated together with the Pydantic schemas.
- **`apps/hermes`**: Composition of `ChatPanel` and `MapView` on the map route, passing viewport, selected event, and focus callback as props.
- **Dependencies and external systems**: New Tavily account/API key and the LangChain dependency set above. No new npm packages are required; the frontend uses native `fetch` and `ReadableStream`.
