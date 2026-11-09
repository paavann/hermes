# Graph Report - hermes  (2026-11-09)

## Corpus Check
- 422 files · ~173,511 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 34 file(s) not represented in the graph (top: (none) 22, .example 4, .css 2)

## Summary
- 4409 nodes · 8890 edges · 299 communities (234 shown, 65 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 1355 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `64a931db`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- search.py
- GeocodingService
- hermes_ai/__init__.py
- package.json
- sqlalchemy
- test_chat_models.py
- services/source.py
- tl_service.py
- asyncio
- api-types.ts
- test_cli.py
- hermes-api
- with
- engine.py
- collections_abc
- TbRateLimiter
- test_chat_engine.py
- planner.py
- with
- uuid
- use-chat.spec.tsx
- steps
- chat_guards.py
- test_event_service.py
- ADDED Requirements
- Requirements
- LlmService
- TlService
- test_chat_web.py
- ChatSource
- enums.py
- test_chat_service.py
- ChatRuntime
- steps
- targets
- Nav.tsx
- chat_service.py
- EventService
- react
- dependencies
- util-types/src/index.ts
- CitationRegistry
- make_uuid
- ADDED Requirements
- ADDED Requirements
- Requirements
- Requirements
- ChatScope
- ParsedArticle
- ._run_create
- AiService
- Hermes Frontend Architecture & Rationale
- use-chat.ts
- sse.ts
- .create_event_with_article
- use-auth-workflow.ts
- chat-store.ts
- citations.py
- nx.json
- compilerOptions
- DueSource
- SyncService
- llm.py
- TestEventModel
- Langfuse
- hermes-ai/tests/test_chat_retriever.py
- .stream
- CitationStreamFilter
- TestEventTlModel
- components.json
- DailyTokenBudget
- chat_retriever.py
- hermes_worker/core/config.py
- NominatimResilienceManager
- coerce_to_str
- GeocodeCacheService
- pytest
- enumerate_tl_pages
- auth.tsx
- react-router
- map-view.tsx
- compilerOptions
- TestSourceModel
- search_timeline_titles
- map/src/lib/config-context.tsx
- React & React Router Standards
- Langfuse Dataset Construction
- v1/events.py
- SlidingWindowRateLimiter
- Hermes — Production Architecture & System Design
- store.ts
- init_db
- test_chat_api.py
- db_lifespan
- command
- BaseArticleFetcher
- TestCreateArticle
- compilerOptions
- compilerOptions
- Hermes API — Architecture & Design Rationale
- test_chat_guards.py
- rss.py
- RSSFetcher
- hermes_db/core/config.py
- ArticleService
- _make_settings
- Hermes Workspace
- Hermes REST API (`hermes-api`)
- v1/tl.py
- core/errors.py
- ConcurrencyGuard
- vite
- compilerOptions
- compilerOptions
- run
- ts/package.json
- ADDED Requirements
- What Changes
- Requirement: Multi-Factor Trending Score Calculation
- openspec-explore/SKILL.md
- .from_settings
- hermes_api/core/config.py
- eslint.config.mjs
- Hermes Ingestion & Lifecycle Worker (`hermes-worker`)
- targets
- TlPanel
- targets
- TestSettingsDefaults
- TestEventScoringMultiFactor
- TestArticleModel
- Decisions
- scripts
- Langfuse Implementation Notes
- opsx-explore.md
- hermes-db
- test_event_fts.py
- TestTimestampMixin
- TestUUIDPrimaryKeyMixin
- compilerOptions
- compilerOptions
- Requirement: Unified Article Fetching Adapter Interface
- Requirement: Unified Article Fetching Adapter Interface
- Hermes: Real-Time Geospatial News Intelligence
- Langfuse Observability
- targets
- entry.server.tsx
- root.tsx
- hermes-e2e/tsconfig.json
- hermes/tsconfig.json
- chat/tsconfig.spec.json
- map/tsconfig.spec.json
- TestGeocodeCacheModel
- util-types/package.json
- overrides
- TypeScript & Frontend Standards
- hermes-api/project.json
- options
- options
- hermes/tsconfig.spec.json
- hermes-worker/project.json
- options
- sync.py
- hermes-ai/project.json
- options
- targets
- hermes-db/project.json
- options
- options
- .test_returns_rowcount_from_cursor_result
- ui-components/tsconfig.json
- ui-components/tsconfig.spec.json
- py/project.json
- options
- targets
- Langfuse v4 project migration
- .client_key
- @playwright/test
- Hermes Worker
- Hermes Worker — Architecture & Design Rationale
- hermes-api
- ui-components/package.json
- util-types/tsconfig.spec.json
- hello.py
- Proposal
- Judge Calibration
- Langfuse Prompt Migration
- clerk-proxy.ts
- ContactSection.tsx
- hermes/package.json
- healthcheck
- chat/package.json
- map/package.json
- test
- env.py
- test
- Tasks
- format
- lint
- .__init__
- test_chat_contract_fixtures.py
- hermes-api/tests/test_config.py
- @react-router/dev
- hermes-e2e/package.json
- hermes/project.json
- format
- lint
- test_import_isolation.py
- context
- hermes-worker
- hermes
- chat/tsconfig.json
- Mapbox & GIS Standards (`libs/map`)
- map/tsconfig.json
- format
- lint
- Hermes DB (`libs/shared/hermes-db`)
- Database Standards
- format
- lint
- TestEventTlStatus
- util-types/tsconfig.json
- format
- lint
- ts/tsconfig.json
- 2. Ingestion Adapter Engine
- hermes-workspace
- tsconfig.json
- Langfuse CI/CD
- Prompt Engineering
- Hermes Application (`apps/hermes`)
- options
- BudgetReservation
- options
- path
- options
- options
- options
- Python Standards
- lock
- lock
- test
- services
- lock
- lock
- test
- lock
- utils-ts.ts
- add
- remove
- sync
- ChatBoundingBox
- update
- add
- sync
- sync
- session_url_exists
- TestSourceType
- TestModelsPackage
- add
- sync
- explanations.md
- @eslint/js@^9.8.0
- @nx/eslint@23.2.1
- @nx/web@23.2.1
- shadcn@^4.21.5
- @swc/helpers@~0.5.18
- @types/react-dom@^19.0.0

## God Nodes (most connected - your core abstractions)
1. `AiConfig` - 72 edges
2. `EventService` - 64 edges
3. `run()` - 64 edges
4. `LlmService` - 61 edges
5. `GeocodingService` - 53 edges
6. `react` - 48 edges
7. `TbRateLimiter` - 46 edges
8. `HermesAi` - 43 edges
9. `ChatRequest` - 37 edges
10. `SearchService` - 36 edges

## Surprising Connections (you probably didn't know these)
- `C. Ingestion & Lifecycle Worker (`apps/hermes-worker`)` --references--> `db_lifespan()`  [INFERRED]
  docs/architecture.md → apps/hermes-worker/src/hermes_worker/core/lifespan.py
- `Risks / Trade-offs` --references--> `SitemapFetcher`  [INFERRED]
  openspec/changes/archive/2026-10-20-multi-source-ingestion-and-ranking/design.md → apps/hermes-worker/src/hermes_worker/services/fetchers/sitemap.py
- `8. Map Integration & App Composition` --references--> `ChatPanel()`  [INFERRED]
  openspec/changes/archive/2026-11-09-add-conversational-rag/tasks.md → libs/chat/src/lib/ui/ChatPanel.tsx
- `4. Elegant & Concise Naming Conventions` --references--> `useEventDetails()`  [INFERRED]
  .agents/rules/ts-standards.md → libs/map/src/lib/hooks/eventDetails.ts
- `13. Frontend chat library and state` --references--> `TlPanel()`  [INFERRED]
  openspec/changes/archive/2026-11-09-add-conversational-rag/design.md → libs/map/src/lib/ui/components/TlPanel.tsx

## Import Cycles
- None detected.

## Communities (299 total, 65 thin omitted)

### Community 0 - "search.py"
Cohesion: 0.07
Nodes (48): _event(), event_fts_expression(), _as_datetime(), _as_float(), _as_int(), _as_optional_float(), _as_optional_int(), BoundingBox (+40 more)

### Community 1 - "GeocodingService"
Cohesion: 0.05
Nodes (41): mock_cache_service(), TestGeocodingService, run(), run(), run(), run(), run(), run() (+33 more)

### Community 2 - "hermes_ai/__init__.py"
Cohesion: 0.06
Nodes (33): Architectural Decisions ("The Why"), Observability & Tracing (Langfuse), TestExtractedEventModel, TestWorkerAiClientFactory, run(), run(), LLM Observability & Tracing (Langfuse), Observability & Langfuse Integration (+25 more)

### Community 3 - "package.json"
Cohesion: 0.04
Nodes (78): devDependencies, autoprefixer@^10.5.4, @babel/core@^7.14.5, @babel/preset-react@^7.14.5, eslint@^9.8.0, eslint-config-prettier@^10.0.0, eslint-plugin-import@2.31.0, eslint-plugin-jsx-a11y@6.10.1 (+70 more)

### Community 4 - "sqlalchemy"
Cohesion: 0.10
Nodes (16): Key Architectural Decisions ("The Why"), Architecture & Boundaries, delete_and_commit(), downgrade(), upgrade(), downgrade(), upgrade(), Base (+8 more)

### Community 5 - "test_chat_models.py"
Cohesion: 0.05
Nodes (27): ChatPlan, PlanTimeRange, BoundingBox, ChatTurn, fallback_plan(), render_history(), sanitize_history(), test_bounding_box_rejects_inverted_latitudes() (+19 more)

### Community 6 - "services/source.py"
Cohesion: 0.07
Nodes (21): _load_sources_config(), SourceConfigEntry, SourceService, sync_sources_from_config(), _make_source(), _mock_session(), test_load_sources_config_file_not_found(), test_load_sources_config_not_a_list() (+13 more)

### Community 7 - "tl_service.py"
Cohesion: 0.08
Nodes (13): WikiSearchException, _fetch_extracts_batch(), fetch_page_extracts(), search_wikipedia(), _extracts_response(), _mock_httpx_response(), _page(), TestEdgeCases (+5 more)

### Community 8 - "asyncio"
Cohesion: 0.11
Nodes (31): HermesAi, AiConfig, base_config(), test_async_context_manager(), _run(), test_call_llm_fallback_on_validation_failure(), test_call_llm_success(), test_exception_hierarchy() (+23 more)

### Community 9 - "api-types.ts"
Cohesion: 0.05
Nodes (38): ChatState, ArticleResponse, ChatCoverage, ChatCoverageLevel, ChatDegradedFlag, ChatDone, ChatDoneEvent, ChatError (+30 more)

### Community 10 - "test_cli.py"
Cohesion: 0.07
Nodes (27): main(), run_app(), setup_logging(), handle_all(), handle_lifecycle(), handle_sync(), WorkerCmd, build_parser() (+19 more)

### Community 11 - "hermes-api"
Cohesion: 0.06
Nodes (47): context, dockerfile, target, resources, path, required, ENV, HOST (+39 more)

### Community 12 - "with"
Cohesion: 0.04
Nodes (46): concurrency, cancel-in-progress, group, if, name, needs, secrets, uses (+38 more)

### Community 13 - "engine.py"
Cohesion: 0.12
Nodes (29): _timeline(), CitationValidation, _plan_filters(), _provenance(), ChatStage, ChatUsage, DoneEvent, ErrorCode (+21 more)

### Community 14 - "collections_abc"
Cohesion: 0.06
Nodes (9): downgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade() (+1 more)

### Community 15 - "TbRateLimiter"
Cohesion: 0.08
Nodes (21): test_rate_limiter_allows_burst_up_to_limit(), _run(), test_rate_limiter_property(), test_rate_limiter_refills_over_time(), _run(), test_rate_limiter_throttles_after_burst(), _run(), test_rate_limiter_acquire() (+13 more)

### Community 16 - "test_chat_engine.py"
Cohesion: 0.18
Nodes (26): WebSearchOutcome, _collect(), run(), _config(), _engine(), _event(), FakeAnswer, FakePlanner (+18 more)

### Community 17 - "planner.py"
Cohesion: 0.07
Nodes (19): PlanRunner, TavilyTool, _config(), _planner(), test_event_scope_is_rendered_in_prompt(), run(), test_planner_drops_unknown_category(), run() (+11 more)

### Community 18 - "with"
Cohesion: 0.05
Nodes (40): if, name, needs, runs-on, steps, name, outputs, runs-on (+32 more)

### Community 19 - "uuid"
Cohesion: 0.07
Nodes (12): setup_logging(), index(), test_get_event_detail_not_found(), test_get_event_detail_success(), test_get_events_by_bbox_success(), test_tl_endpoint_post(), TestCleanLocationName, get_db() (+4 more)

### Community 20 - "use-chat.spec.tsx"
Cohesion: 0.07
Nodes (27): MapChat(), MapChatProps, ChatConfig, ChatConfigContext, ChatConfigProvider(), ChatConfigProviderProps, ChatStreamFn, autoScope (+19 more)

### Community 21 - "steps"
Cohesion: 0.06
Nodes (39): name, outputs, runs-on, steps, concurrency, cancel-in-progress, group, if (+31 more)

### Community 22 - "chat_guards.py"
Cohesion: 0.09
Nodes (16): Architecture & Framework (FastAPI), Backend & FastAPI Standards, Models / Schemas, AppException, ChatBudgetExhausted, ChatBusy, ChatRateLimitExceeded, ChatUnavailable (+8 more)

### Community 23 - "test_event_service.py"
Cohesion: 0.08
Nodes (15): GeopoliticalBloc, calculate_shannon_diversity(), calculate_velocity(), calculate_velocity_multiplier(), boost_multiplier(), reciprocal_rank_fusion(), _patch_article_create(), TestCalculateShannonDiversity (+7 more)

### Community 24 - "ADDED Requirements"
Cohesion: 0.05
Nodes (38): ADDED Requirements, Purpose, Requirement: Bounded web search escalation, Requirement: Citation-bearing current-affairs claims, Requirement: Citation validation and provenance, Requirement: Explicit background knowledge labeling, Requirement: External evidence disclosure, Requirement: Planner-driven retrieval query (+30 more)

### Community 25 - "Requirements"
Cohesion: 0.05
Nodes (38): Conversational RAG Specification, Purpose, Requirement: Bounded web search escalation, Requirement: Citation-bearing current-affairs claims, Requirement: Citation validation and provenance, Requirement: Explicit background knowledge labeling, Requirement: External evidence disclosure, Requirement: Planner-driven retrieval query (+30 more)

### Community 26 - "LlmService"
Cohesion: 0.10
Nodes (19): Architectural Decisions ("The Why"), 7. Model Routing, Failover & Geocoding Resiliency, Schema-Level Validation Failover, ChatEngine, ChatPlanner, ConfigurationError, LlmService, test_planner_requires_plan_group() (+11 more)

### Community 27 - "TlService"
Cohesion: 0.16
Nodes (19): TlResponse, TlService, dummy_event(), mock_ai_extraction(), mock_geocoding(), mock_tl_db(), test_concurrent_generation_returns_generating(), run_test() (+11 more)

### Community 28 - "test_chat_web.py"
Cohesion: 0.11
Nodes (24): _as_float(), parse_published_at(), sanitize_text(), source_name_from_url(), validated_url(), WebSearchService, _config(), FailingTool (+16 more)

### Community 29 - "ChatSource"
Cohesion: 0.12
Nodes (30): citationClass(), CitationKind, CitationMarkerSegment, CitationRenderOptions, CitationSegment, CitationTextSegment, citationTitle(), CLICKABLE_CLASS (+22 more)

### Community 30 - "enums.py"
Cohesion: 0.08
Nodes (12): get_events(), test_get_events_with_scope_parameter(), CredibilityTier, EventScope, EventStatus, ImpactLevel, TestCredibilityTier, TestEventScope (+4 more)

### Community 31 - "test_chat_service.py"
Cohesion: 0.14
Nodes (26): _done(), FakeEngine, FakeRequest, _frames(), _guards(), _service(), _source(), test_closing_the_stream_releases_guards() (+18 more)

### Community 32 - "ChatRuntime"
Cohesion: 0.09
Nodes (9): create_chat_stream(), get_chat_service(), ChatGuards, ChatRuntime, ChatService, PreparedTurn, _usage_tokens(), FakeRuntime (+1 more)

### Community 33 - "steps"
Cohesion: 0.06
Nodes (33): name, outputs, runs-on, steps, concurrency, cancel-in-progress, group, if (+25 more)

### Community 34 - "targets"
Cohesion: 0.07
Nodes (33): executor, options, executor, options, executor, options, executor, options (+25 more)

### Community 35 - "Nav.tsx"
Cohesion: 0.11
Nodes (18): CapabilitiesSection(), CAPABILITY_CARDS, HeroSection(), LaunchMapBtn(), LaunchMapBtnProps, Nav(), NAV_ITEMS, NavProps (+10 more)

### Community 36 - "chat_service.py"
Cohesion: 0.16
Nodes (23): ChatCoverage, ChatDone, ChatDoneEvent, ChatError, ChatErrorEvent, ChatEventScope, ChatGlobalScope, ChatHistoryMessage (+15 more)

### Community 37 - "EventService"
Cohesion: 0.15
Nodes (5): EventService, make_async_session(), TestArticleUrlExistsDelegation, TestGetActiveEvents, TestGetActiveEventsByEmbeddings

### Community 38 - "react"
Cohesion: 0.12
Nodes (17): Button(), ButtonProps, buttonVariants, InputProps, LabelProps, SeparatorProps, TextareaProps, BootSequenceProps (+9 more)

### Community 39 - "dependencies"
Cohesion: 0.07
Nodes (30): dependencies, axios@^1.20.0, @base-ui/react@^1.9.0, class-variance-authority@^0.7.1, @clerk/react-router@^3.6.35, clsx@^2.1.1, cn@^0.4.0, @fontsource-variable/jetbrains-mono@^5.3.0 (+22 more)

### Community 40 - "util-types/src/index.ts"
Cohesion: 0.12
Nodes (16): 3. Monorepo UI Architecture & Strict shadcn Discipline, citedEventsFromSources(), DynamicMapContainer, HydrateFallback(), loader(), MAP_CONFIG, MapLoadingFallback(), MapRoute() (+8 more)

### Community 41 - "CitationRegistry"
Cohesion: 0.16
Nodes (15): CitationRegistry, build_answer_messages(), clean_xml_text(), format_evidence(), _iso(), _tag(), _event(), test_answer_messages_include_rules_scope_and_question() (+7 more)

### Community 42 - "make_uuid"
Cohesion: 0.15
Nodes (6): make_article(), make_event(), make_source(), make_uuid(), utcnow(), TestAddArticleToEvent

### Community 43 - "ADDED Requirements"
Cohesion: 0.07
Nodes (28): ADDED Requirements, Purpose, Requirement: Citation-driven map focus, Requirement: No autonomous map control, Requirement: Persistent cited-pin highlighting, Requirement: Recoverable streaming failure, Requirement: Scope defaults from map state, Requirement: Simultaneous chat and map visibility (+20 more)

### Community 44 - "ADDED Requirements"
Cohesion: 0.07
Nodes (28): ADDED Requirements, Purpose, Requirement: Bounded recency and trending boosts, Requirement: Complete retrieval context, Requirement: Coverage signal for web escalation, Requirement: Eligibility window, Requirement: Hybrid lexical and semantic retrieval, Requirement: Planner-supplied filters (+20 more)

### Community 45 - "Requirements"
Cohesion: 0.07
Nodes (28): Chat Map Integration Specification, Purpose, Requirement: Citation-driven map focus, Requirement: No autonomous map control, Requirement: Persistent cited-pin highlighting, Requirement: Recoverable streaming failure, Requirement: Scope defaults from map state, Requirement: Simultaneous chat and map visibility (+20 more)

### Community 46 - "Requirements"
Cohesion: 0.07
Nodes (28): Event Retrieval Specification, Purpose, Requirement: Bounded recency and trending boosts, Requirement: Complete retrieval context, Requirement: Coverage signal for web escalation, Requirement: Eligibility window, Requirement: Hybrid lexical and semantic retrieval, Requirement: Planner-supplied filters (+20 more)

### Community 47 - "ChatScope"
Cohesion: 0.15
Nodes (13): fake_search_service(), FakeEmbeddingClient, FakeSearchService, FakeSession, _result(), _retriever(), factory(), test_embedding_failure_falls_back_to_lexical_search() (+5 more)

### Community 48 - "ParsedArticle"
Cohesion: 0.14
Nodes (11): ParsedArticle, _truncate_to_words(), _extract_article_from_html(), _parse_sitemap_urls(), SitemapFetcher, test_extract_article_from_html(), test_parse_sitemap_urls(), _run() (+3 more)

### Community 50 - "AiService"
Cohesion: 0.15
Nodes (5): AiService, ai_service(), TestAnalyzeTlContext, TestExtractTl, TestRouterFallback

### Community 51 - "Hermes Frontend Architecture & Rationale"
Cohesion: 0.08
Nodes (23): 1. Application Role & Architecture Boundary, 2. Server-Side Rendering (`ssr: true`) & Authentication Guarding, 3. WebGL Canvas Isolation & SSR Boundary Analysis, 4. Map Rendering & Interaction Boundaries, 5. Design System Integration, 6. Provider Composition & Data Boundaries, 8. Production Hosting & Network Topology, Authentication Guarding (+15 more)

### Community 52 - "use-chat.ts"
Cohesion: 0.17
Nodes (21): Composition, useChatConfig(), AutoScope, lastUserIndex(), resolveScope(), useChat(), UseChatResult, ChatScopeMode (+13 more)

### Community 53 - "sse.ts"
Cohesion: 0.15
Nodes (22): Transport, ChatTransportError, ChatTransportErrorInit, decodeEvent(), ERROR_CODES, ErrorEnvelope, EVENT_TYPES, isChatErrorCode() (+14 more)

### Community 54 - ".create_event_with_article"
Cohesion: 0.16
Nodes (6): EventExtractionData, GeocodingData, DummyExtraction, DummyGeocoding, test_protocols_conformance(), test_ranking_constants()

### Community 55 - "use-auth-workflow.ts"
Cohesion: 0.23
Nodes (16): EmailStep(), EmailStepProps, OtpStep(), OtpStepProps, PasswordStep(), PasswordStepProps, SetupStep(), SetupStepProps (+8 more)

### Community 56 - "chat-store.ts"
Cohesion: 0.12
Nodes (19): Citations, Composition, @hermes/chat, Scope contract, Store, Testing, assistantMessage(), buildHistory() (+11 more)

### Community 57 - "citations.py"
Cohesion: 0.16
Nodes (15): _article_source(), ArticleEvidence, _event_source(), EventEvidence, _normalize_marker(), _parse_date(), _timeline_source(), TimelineEdgeEvidence (+7 more)

### Community 58 - "nx.json"
Cohesion: 0.08
Nodes (23): analytics, babel, bundler, linter, style, style, generators, @nx/react (+15 more)

### Community 59 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, composite, customConditions, declarationMap, emitDeclarationOnly, importHelpers, isolatedModules, lib (+15 more)

### Community 60 - "DueSource"
Cohesion: 0.21
Nodes (16): _extract_domain(), GDELTFetcher, _parse_gdelt_date(), test_extract_domain(), test_gdelt_fetcher_malformed_json(), _run(), test_gdelt_fetcher_rate_limit_circuit_breaker(), _run() (+8 more)

### Community 61 - "SyncService"
Cohesion: 0.17
Nodes (11): SyncService, _process_source(), dummy_due_source(), TestSyncService, run(), run(), run(), run() (+3 more)

### Community 62 - "llm.py"
Cohesion: 0.11
Nodes (10): _clean_json_str(), _deployment(), _is_sensitive_otel_key(), _mask_data(), _mask_otel_spans(), _validate_group(), test_ai_config_chat_fields(), test_ai_config_defaults() (+2 more)

### Community 64 - "Langfuse"
Cohesion: 0.09
Nodes (19): Credentials, Discovery, Install, Langfuse CLI Reference, Tips, Skill Feedback, Submission options, 1. Langfuse API via CLI (+11 more)

### Community 65 - "hermes-ai/tests/test_chat_retriever.py"
Cohesion: 0.10
Nodes (10): 4. Conversational RAG Pipeline (`POST /api/v1/chat`), Guards and Kill Switch, Scope Resolution & Retrieval, SSE Contract, ChatRetriever, FakeRetriever, test_chat_retriever_module_does_not_import_hermes_db(), test_fake_retriever_conforms_to_protocol() (+2 more)

### Community 66 - ".stream"
Cohesion: 0.12
Nodes (8): AnswerModel, _chunk_text(), _close_stream(), _int(), _merge_usage(), Planner, WebSearcher, PlannerOutcome

### Community 67 - "CitationStreamFilter"
Cohesion: 0.25
Nodes (14): CitationStreamFilter, finalize_answer(), _registry(), test_finalize_answer_filters_unknown_ids_and_tracks_background(), test_finalize_answer_reports_no_citations(), test_registry_assigns_stable_markers_in_order(), test_registry_resolves_sources_with_parent_coordinates(), test_sources_for_deduplicates_in_first_citation_order() (+6 more)

### Community 69 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 70 - "DailyTokenBudget"
Cohesion: 0.24
Nodes (5): DailyTokenBudget, test_budget_reconciliation_records_actual_usage_once(), test_budget_rejects_and_resets_at_utc_midnight(), test_budget_reservation_release_frees_the_estimate(), test_budget_zero_disables_accounting()

### Community 71 - "chat_retriever.py"
Cohesion: 0.15
Nodes (9): _article(), DbChatRetriever, EmbeddingClient, _evidence(), _retrieval_result(), _search_bbox(), _search_filters(), _search_scope() (+1 more)

### Community 72 - "hermes_worker/core/config.py"
Cohesion: 0.15
Nodes (6): get_settings(), Settings, _make_settings(), TestGetSettings, TestWorkerDbUrl, TestWorkerSettingsDefaults

### Community 73 - "NominatimResilienceManager"
Cohesion: 0.12
Nodes (15): 3. The Grounded Geocoding Shield, Defense Mechanisms, 1. Commands, 2. Invariants, 3. Tunables, 4. Domain Triggers, Hermes AI (`libs/shared/hermes-ai`), Configuration (`AiConfig`) (+7 more)

### Community 75 - "GeocodeCacheService"
Cohesion: 0.20
Nodes (4): GeocodeCacheEntry, GeocodeCacheService, TestGetByLocationName, TestSaveGeocodeResult

### Community 76 - "pytest"
Cohesion: 0.21
Nodes (12): ChatRequest, test_discriminated_scope_parses_each_variant(), test_event_scope_requires_event_id(), test_request_defaults_to_global_scope(), test_request_json_snapshot(), test_request_rejects_bad_role(), test_request_rejects_more_than_sixteen_messages(), test_request_rejects_oversized_message_and_history_content() (+4 more)

### Community 77 - "enumerate_tl_pages"
Cohesion: 0.19
Nodes (4): enumerate_tl_pages(), _sort_timeline_titles(), TestEnumerateTlPages, TestSortTimelineTitles

### Community 78 - "auth.tsx"
Cohesion: 0.15
Nodes (12): AuthCheckerboardPattern(), computeCheckerboardLayout(), SsoCallbackView(), CheckerboardLayout, SquareCell, extractClerkError(), useAuthWorkflow(), Auth() (+4 more)

### Community 79 - "react-router"
Cohesion: 0.21
Nodes (10): Footer(), PrivacyNav(), PRIVACY_SECTIONS, PrivacyPolicyContent(), PrivacySection, meta(), PrivacyRoute(), HermesWordmark() (+2 more)

### Community 80 - "map-view.tsx"
Cohesion: 0.21
Nodes (12): 7. Conversational RAG UI & Map Integration, Citation Focus, Highlight Lifecycle, Scope Resolution, 5. Spatial Deduplication Conventions, useMapStore, EventPopup(), getOutletTag() (+4 more)

### Community 81 - "compilerOptions"
Cohesion: 0.11
Nodes (17): compilerOptions, allowJs, esModuleInterop, forceConsistentCasingInFileNames, jsx, lib, outDir, resolveJsonModule (+9 more)

### Community 83 - "search_timeline_titles"
Cohesion: 0.18
Nodes (4): search_timeline_titles(), _search_response(), TestSearchTimelineTitles, capturing_get()

### Community 84 - "map/src/lib/config-context.tsx"
Cohesion: 0.18
Nodes (12): 1. Commands, 2. Invariants, 3. Domain Triggers, Hermes Map (`libs/map`), MapConfig, MapConfigContext, useMapConfig(), useMapDataSync() (+4 more)

### Community 85 - "React & React Router Standards"
Cohesion: 0.13
Nodes (15): 1. Official Documentation Mandate, 2. Directory Structure & The 80/20 Shell Doctrine, 4. Tailwind CSS v4 & Tactical Styling Discipline, 5. Modern React 19 Paradigms, 6. The "You Might Not Need an Effect" Doctrine, 7. The 6-Tier State Management Hierarchy, 8. Tactical GIS & Mapbox Architecture, 9. Component Hygiene & Render Purity (+7 more)

### Community 86 - "Langfuse Dataset Construction"
Cohesion: 0.12
Nodes (13): Critical Rules, Langfuse Dataset Construction, Primary Guide, Workflow, 1. Determine Online or Offline, 2. Establish the Metric Set, 3. Implement and Verify, Setting up evals (+5 more)

### Community 87 - "v1/events.py"
Cohesion: 0.23
Nodes (9): get_event(), get_event_service(), get_events_by_bbox(), ArticleResponse, EventDetailResponse, EventResponse, MapEventResponse, TlEdgeResponse (+1 more)

### Community 88 - "SlidingWindowRateLimiter"
Cohesion: 0.17
Nodes (4): SlidingWindowRateLimiter, FakeClock, test_rate_limiter_is_per_key(), test_rate_limiter_rejects_with_retry_after()

### Community 89 - "Hermes — Production Architecture & System Design"
Cohesion: 0.12
Nodes (16): 1. High-Level Production Topology, 2. Infrastructure & Hosting Topology, 3. Data Ingestion & Consensus Pipeline, 4. Multi-Factor Trending & Ranking Algorithm, 5. Spatial Query & WebGL Viewport Synchronization, 6. Causality Timeline Synthesis Engine, 9. CI/CD & Deployment Workflows, A. Frontend Application (`apps/hermes`) (+8 more)

### Community 90 - "store.ts"
Cohesion: 0.17
Nodes (11): BoundingBox, CitedEvent, FocusRequest, MapState, firstEvent, secondEvent, CitedEventFeature, CitedEventProperties (+3 more)

### Community 92 - "test_chat_api.py"
Cohesion: 0.24
Nodes (7): _app(), FakeChatService, test_chat_route_is_503_when_runtime_is_missing(), test_chat_route_rejects_invalid_body_with_422(), test_chat_route_rejects_malformed_bbox(), test_chat_route_returns_429_with_retry_after(), test_chat_route_streams_events_in_order()

### Community 93 - "db_lifespan"
Cohesion: 0.17
Nodes (10): 1. Cloud Infrastructure & Ephemeral Execution Model, Architectural Rationale: Why Ephemeral Compute?, Architecture Topology, Lifecycle of an Ephemeral Execution, Key Architectural Invariants, db_lifespan(), test_db_lifespan(), _test() (+2 more)

### Community 94 - "command"
Cohesion: 0.17
Nodes (15): command, cwd, executor, options, executor, executor, options, options (+7 more)

### Community 95 - "BaseArticleFetcher"
Cohesion: 0.14
Nodes (12): BaseArticleFetcher, 1. Ingestion Adapter Architecture & `TbRateLimiter` Extension, 2. Shannon Diversity Entropy Across 5 Geopolitical Blocs, 3. Submodular Diminishing Returns for Syndicated Wires, 4. Zero-Overhead Severity Triage in LLM Extraction, 5. Continuous Exponential Half-Life Decay, Context, Decisions (+4 more)

### Community 97 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, emitDeclarationOnly, forceConsistentCasingInFileNames, module, moduleResolution, outDir, rootDir, tsBuildInfoFile (+6 more)

### Community 98 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, emitDeclarationOnly, forceConsistentCasingInFileNames, module, moduleResolution, outDir, rootDir, tsBuildInfoFile (+6 more)

### Community 99 - "Hermes API — Architecture & Design Rationale"
Cohesion: 0.14
Nodes (14): 1. Application Role & Architectural Boundaries, 2. Spatial Viewport Query Pipeline, 3. Timeline Engine Orchestration Pipeline, 5. Cloud Infrastructure & Production Hosting (Amazon Lightsail), 6. CORS Exception Handling Architecture, 8. Observability & Langfuse Tracing, Compute Sizing & Memory Mechanics ("The Why"), Edge Ingress & Zero-Downtime Deployments (+6 more)

### Community 100 - "test_chat_guards.py"
Cohesion: 0.21
Nodes (8): estimate_tokens(), hash_client_ip(), _guards(), _request(), test_chat_guards_hash_client_key_and_rate_limit(), test_chat_guards_uses_forwarded_header_only_when_trusted(), test_client_ip_hash_is_salted_and_stable(), test_estimate_tokens_includes_output_budget()

### Community 101 - "rss.py"
Cohesion: 0.24
Nodes (4): _extract_content(), fetch_feed(), _parse_date(), TestRssHelpers

### Community 102 - "RSSFetcher"
Cohesion: 0.20
Nodes (8): RSSFetcher, _run(), TestFetchFeed, run(), run(), run(), run(), run()

### Community 103 - "hermes_db/core/config.py"
Cohesion: 0.19
Nodes (3): get_settings(), Settings, TestGetSettings

### Community 106 - "Hermes Workspace"
Cohesion: 0.15
Nodes (12): 1. Commands, 2. Invariants, 3. Conventions, 4. Gotchas & Landmines, 5. Boundaries & Environment, 6. Domain Triggers, AWS Guidance for the new AWS experience, Constraints: (+4 more)

### Community 107 - "Hermes REST API (`hermes-api`)"
Cohesion: 0.15
Nodes (11): 1. Spatial Viewport Bounding Box (`GET /api/v1/events/bbox`), 2. Event List Query (`GET /api/v1/events/`), 3. On-Demand Timeline Synthesis (`POST /api/v1/events/tl/{event_id}`), 4. Conversational Chat (`POST /api/v1/chat`), Configuration & Environment Variables, Development Runbook, Endpoints Overview, Hermes REST API (`hermes-api`) (+3 more)

### Community 108 - "v1/tl.py"
Cohesion: 0.18
Nodes (3): analyze_event_tl(), get_tl_service(), ErrorResponseSchema

### Community 109 - "core/errors.py"
Cohesion: 0.22
Nodes (7): _cors_headers(), register_err_handlers(), app_exception_handler(), http_exception_handler(), universal_exception_handler(), validation_exception_handler(), 11. Cost, rate, and concurrency guards

### Community 110 - "ConcurrencyGuard"
Cohesion: 0.21
Nodes (3): ConcurrencyGuard, test_concurrency_guard_times_out_and_releases_slots(), run()

### Community 111 - "vite"
Cohesion: 0.19
Nodes (7): env, @tailwindcss/vite@^4.3.3, vite@^8.0.0, @vitejs/plugin-react@^6.0.0, @tailwindcss/vite, vite, @vitejs/plugin-react

### Community 112 - "compilerOptions"
Cohesion: 0.15
Nodes (12): compilerOptions, jsx, lib, outDir, rootDir, tsBuildInfoFile, types, exclude (+4 more)

### Community 113 - "compilerOptions"
Cohesion: 0.15
Nodes (12): compilerOptions, jsx, lib, outDir, rootDir, tsBuildInfoFile, types, exclude (+4 more)

### Community 115 - "ts/package.json"
Cohesion: 0.15
Nodes (12): dependencies, exports, ./package.json, main, name, nx, name, tags (+4 more)

### Community 116 - "ADDED Requirements"
Cohesion: 0.15
Nodes (12): ADDED Requirements, Purpose, Requirement: Continuous Half-Life Decay, Requirement: Multi-Factor Trending Score Calculation, Requirement: Real-World Severity Classification, Scenario: Breaking velocity boost, Scenario: Critical global crisis classification, Scenario: Cross-border consensus amplification (+4 more)

### Community 117 - "What Changes"
Cohesion: 0.15
Nodes (12): Capabilities, Conversational interface, Deferred, Grounded answer pipeline, Impact, Local retrieval, Modified Capabilities, New Capabilities (+4 more)

### Community 118 - "Requirement: Multi-Factor Trending Score Calculation"
Cohesion: 0.15
Nodes (12): Event Ranking Specification, Purpose, Requirement: Continuous Half-Life Decay, Requirement: Multi-Factor Trending Score Calculation, Requirement: Real-World Severity Classification, Requirements, Scenario: Breaking velocity boost, Scenario: Critical global crisis classification (+4 more)

### Community 119 - "openspec-explore/SKILL.md"
Cohesion: 0.17
Nodes (11): Check for context, Ending Discovery, Guardrails, Handling Different Entry Points, OpenSpec Awareness, Planning a Change, The Stance, What You Don't Have To Do (+3 more)

### Community 120 - ".from_settings"
Cohesion: 0.17
Nodes (7): 1. Commands, 2. Invariants, 3. Domain Triggers, Hermes API (`apps/hermes-api`), 7. Lifespan & Resilience Guarantees, lifespan(), _pair()

### Community 121 - "hermes_api/core/config.py"
Cohesion: 0.20
Nodes (4): get_settings(), Settings, test_lifespan_initializes_and_closes_db(), _test()

### Community 122 - "eslint.config.mjs"
Cohesion: 0.23
Nodes (4): eslint-plugin-playwright@^1.6.2, @nx/eslint-plugin@23.2.1, eslint-plugin-playwright, @nx/eslint-plugin

### Community 123 - "Hermes Ingestion & Lifecycle Worker (`hermes-worker`)"
Cohesion: 0.17
Nodes (7): CLI Commands & Targets, Configuration & Environment Variables, Development Runbook, Hermes Ingestion & Lifecycle Worker (`hermes-worker`), Ingestion Pipeline Stages, Observability & Tracing (Langfuse), Operational Model & Cloud Topology

### Community 124 - "targets"
Cohesion: 0.17
Nodes (12): executor, options, executor, executor, options, executor, options, targets (+4 more)

### Community 125 - "TlPanel"
Cohesion: 0.24
Nodes (10): useTl(), addLayersToMap(), buildGeoJson(), removeLayersFromMap(), TlPanel(), Context, Design, Goals / Non-Goals (+2 more)

### Community 126 - "targets"
Cohesion: 0.17
Nodes (12): executor, options, executor, executor, options, targets, add, install (+4 more)

### Community 128 - "TestEventScoringMultiFactor"
Cohesion: 0.23
Nodes (3): _Extraction, _flush(), TestEventScoringMultiFactor

### Community 130 - "Decisions"
Cohesion: 0.17
Nodes (12): 10. SSE API contract and lifecycle, 12. Observability and privacy, 13. Frontend chat library and state, 14. Map integration and highlighting, 2. LangChain as orchestration, LiteLLM Router as transport, 4. Hybrid retrieval and reciprocal rank fusion, 5. Scope, eligibility, filters, and coverage, 6. Evidence assembly and source registry (+4 more)

### Community 131 - "scripts"
Cohesion: 0.17
Nodes (12): scripts, env:push:api, env:push:ui, install:all, lint, lint:py, lock, setup (+4 more)

### Community 132 - "Langfuse Implementation Notes"
Cohesion: 0.18
Nodes (10): Annotation queues, Annotation target: OBSERVATION versus TRACE, Common gotchas, Credentials, Error Analysis, Langfuse Implementation Notes, Primary Guide, Prompt fixes (+2 more)

### Community 133 - "opsx-explore.md"
Cohesion: 0.18
Nodes (10): Check for context, Ending Discovery, Guardrails, OpenSpec Awareness, Planning a Change, The Stance, What You Don't Have To Do, What You Might Do (+2 more)

### Community 134 - "hermes-db"
Cohesion: 0.18
Nodes (11): dockerfile_inline, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, build, env_file, environment, ports (+3 more)

### Community 135 - "test_event_fts.py"
Cohesion: 0.22
Nodes (4): _index_expression(), _load_migration(), test_fts_index_registered_in_metadata(), test_metadata_expression_matches_migration()

### Community 138 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, jsx, outDir, rootDir, tsBuildInfoFile, types, exclude, extends (+2 more)

### Community 139 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, forceConsistentCasingInFileNames, module, moduleResolution, outDir, types, extends, include (+2 more)

### Community 140 - "Requirement: Unified Article Fetching Adapter Interface"
Cohesion: 0.18
Nodes (10): ADDED Requirements, Purpose, Requirement: Ingestion Rate Limiting and Circuit Breaker, Requirement: Unified Article Fetching Adapter Interface, Scenario: Fallback HTML article extraction, Scenario: Fetching from standard RSS feed, Scenario: Fetching wire articles via GDELT 2.0, Scenario: Provider rate limit encountered (+2 more)

### Community 141 - "Requirement: Unified Article Fetching Adapter Interface"
Cohesion: 0.18
Nodes (10): News Ingestion Specification, Purpose, Requirement: Ingestion Rate Limiting and Circuit Breaker, Requirement: Unified Article Fetching Adapter Interface, Requirements, Scenario: Fallback HTML article extraction, Scenario: Fetching from standard RSS feed, Scenario: Fetching wire articles via GDELT 2.0 (+2 more)

### Community 142 - "Hermes: Real-Time Geospatial News Intelligence"
Cohesion: 0.18
Nodes (11): Component Breakdown, Core Capabilities, Documentation, Getting Started, Hermes: Real-Time Geospatial News Intelligence, Installation & Local Setup, License, Overview (+3 more)

### Community 143 - "Langfuse Observability"
Cohesion: 0.20
Nodes (9): 1. Assess Current State, 2. Verify Baseline Requirements, 3. Run and Self-Audit the Traces (required), 4. Explore Traces With the User, Always Explain Why, Common Mistakes, Langfuse Observability, Multi-agent systems (subagent dispatch) (+1 more)

### Community 144 - "targets"
Cohesion: 0.20
Nodes (10): executor, targets, install, test, update, cache, executor, outputs (+2 more)

### Community 145 - "entry.server.tsx"
Cohesion: 0.20
Nodes (7): streamTimeout, isbot@^4.4.0, react-dom@^19.2.8, @react-router/node@^8.3.1, isbot, react-dom, @react-router/node

### Community 146 - "root.tsx"
Cohesion: 0.20
Nodes (4): AppProps, clerkAuthMiddleware, middleware, RootErrorBoundaryProps

### Community 147 - "hermes-e2e/tsconfig.json"
Cohesion: 0.20
Nodes (9): compilerOptions, allowJs, outDir, sourceMap, types, exclude, extends, include (+1 more)

### Community 148 - "hermes/tsconfig.json"
Cohesion: 0.20
Nodes (9): compilerOptions, jsx, moduleResolution, types, extends, files, include, ../../tsconfig.base.json (+1 more)

### Community 149 - "chat/tsconfig.spec.json"
Cohesion: 0.20
Nodes (9): compilerOptions, jsx, lib, outDir, types, extends, include, ../../tsconfig.base.json (+1 more)

### Community 150 - "map/tsconfig.spec.json"
Cohesion: 0.20
Nodes (9): compilerOptions, jsx, lib, outDir, types, extends, include, ../../tsconfig.base.json (+1 more)

### Community 152 - "util-types/package.json"
Cohesion: 0.20
Nodes (9): dependencies, exports, ./package.json, main, name, private, type, types (+1 more)

### Community 153 - "overrides"
Cohesion: 0.20
Nodes (10): overrides, axios, body-parser, brace-expansion, fast-uri, follow-redirects, qs, smol-toml (+2 more)

### Community 154 - "TypeScript & Frontend Standards"
Cohesion: 0.22
Nodes (8): 1. Agent Mandate & Core Principles, 2. Strict Type Safety & Prohibitions, 3. Type Modeling: Types, Interfaces & Enums, 4. Elegant & Concise Naming Conventions, 5. Monorepo Boundaries & Import Discipline, 6. React, State & Tactical GIS Architecture, 7. Formatting & Code Hygiene, TypeScript & Frontend Standards

### Community 155 - "hermes-api/project.json"
Cohesion: 0.22
Nodes (8): name, projectType, release, version, $schema, sourceRoot, tags, versionActions

### Community 156 - "options"
Cohesion: 0.22
Nodes (9): cache, executor, options, outputs, bundleLocalDependencies, lockedVersions, outputPath, publish (+1 more)

### Community 157 - "options"
Cohesion: 0.28
Nodes (9): executor, options, command, cwd, executor, options, migrate, serve (+1 more)

### Community 158 - "hermes/tsconfig.spec.json"
Cohesion: 0.22
Nodes (8): compilerOptions, jsx, outDir, types, extends, include, ../../tsconfig.base.json, references

### Community 159 - "hermes-worker/project.json"
Cohesion: 0.22
Nodes (8): name, projectType, release, version, $schema, sourceRoot, tags, versionActions

### Community 160 - "options"
Cohesion: 0.22
Nodes (9): cache, executor, options, outputs, bundleLocalDependencies, lockedVersions, outputPath, publish (+1 more)

### Community 161 - "sync.py"
Cohesion: 0.25
Nodes (3): create_ai_client(), run(), run()

### Community 162 - "hermes-ai/project.json"
Cohesion: 0.22
Nodes (8): name, projectType, release, version, $schema, sourceRoot, tags, versionActions

### Community 163 - "options"
Cohesion: 0.22
Nodes (9): cache, executor, options, outputs, bundleLocalDependencies, lockedVersions, outputPath, publish (+1 more)

### Community 164 - "targets"
Cohesion: 0.22
Nodes (9): executor, executor, options, targets, install, remove, update, executor (+1 more)

### Community 165 - "hermes-db/project.json"
Cohesion: 0.22
Nodes (8): name, projectType, release, version, $schema, sourceRoot, tags, versionActions

### Community 166 - "options"
Cohesion: 0.22
Nodes (9): cache, executor, options, outputs, bundleLocalDependencies, lockedVersions, outputPath, publish (+1 more)

### Community 167 - "options"
Cohesion: 0.28
Nodes (9): executor, options, executor, options, command, cwd, makemigrations, migrate (+1 more)

### Community 169 - "ui-components/tsconfig.json"
Cohesion: 0.22
Nodes (8): compilerOptions, baseUrl, paths, extends, files, include, ../../../tsconfig.base.json, references

### Community 170 - "ui-components/tsconfig.spec.json"
Cohesion: 0.22
Nodes (8): compilerOptions, jsx, outDir, types, extends, include, ../../../tsconfig.base.json, references

### Community 171 - "py/project.json"
Cohesion: 0.22
Nodes (8): name, projectType, release, version, $schema, sourceRoot, tags, versionActions

### Community 172 - "options"
Cohesion: 0.22
Nodes (9): cache, executor, options, outputs, bundleLocalDependencies, lockedVersions, outputPath, publish (+1 more)

### Community 173 - "targets"
Cohesion: 0.22
Nodes (9): executor, executor, options, targets, install, remove, update, executor (+1 more)

### Community 174 - "Langfuse v4 project migration"
Cohesion: 0.25
Nodes (7): Choose the execution mode, Langfuse v4 project migration, Migrate evaluators, Migrate exports, Migrate the codebase, Sources of truth, Validate and report

### Community 176 - "@playwright/test"
Cohesion: 0.25
Nodes (6): @nx/devkit@23.2.1, @nx/playwright@23.2.1, @playwright/test@^1.37.0, @nx/devkit, @nx/playwright, @playwright/test

### Community 177 - "Hermes Worker"
Cohesion: 0.25
Nodes (7): 1. Commands, 2. Boundaries, 3. Invariants, 4. Runtime & Memory, 5. Tunables, 6. Triggers, Hermes Worker

### Community 178 - "Hermes Worker — Architecture & Design Rationale"
Cohesion: 0.25
Nodes (8): 2. Ingestion Pipeline & Token Optimization, 4. Multi-Factor Scoring & Consensus Formulation, 5. Lifecycle Decay & Status Transitions, 6. Observability & Langfuse Tracing, A. Embed Before Extract (Vector Pre-Filtering), Architectural Decisions ("The Why"), B. Bounded Batch Sizing & Memory Limits, Hermes Worker — Architecture & Design Rationale

### Community 179 - "hermes-api"
Cohesion: 0.25
Nodes (8): hermes-db, depends_on, ports, restart, volumes, condition, depends_on, hermes-api

### Community 180 - "ui-components/package.json"
Cohesion: 0.25
Nodes (7): dependencies, exports, ./package.json, main, name, types, version

### Community 181 - "util-types/tsconfig.spec.json"
Cohesion: 0.25
Nodes (7): compilerOptions, outDir, resolveJsonModule, types, extends, include, ../../../tsconfig.base.json

### Community 183 - "Proposal"
Cohesion: 0.25
Nodes (7): Capabilities, Impact, Modified Capabilities, New Capabilities, Proposal, What Changes, Why

### Community 184 - "Judge Calibration"
Cohesion: 0.29
Nodes (6): 1. Prepare the calibration, 2. Run the calibration, 3. Review the results, 4. Iterate until the judge is approved, 5. Deploy the approved judge, Judge Calibration

### Community 185 - "Langfuse Prompt Migration"
Cohesion: 0.29
Nodes (6): 1. Inventory every prompt (before writing any code), 2. Convert templating and decide structure, 3. Present the plan, then create and refactor, 4. Verify, Langfuse Prompt Migration, Prerequisites

### Community 186 - "clerk-proxy.ts"
Cohesion: 0.38
Nodes (5): Frontend & React Standards, TanStack Query Best Practices, action(), handleClerkProxy(), loader()

### Community 187 - "ContactSection.tsx"
Cohesion: 0.38
Nodes (6): AccessSection, ContactFormData, ContactSection(), SendMessageBtn(), SendMessageBtnProps, Textarea()

### Community 188 - "hermes/package.json"
Cohesion: 0.29
Nodes (6): name, private, scripts, build, sideEffects, type

### Community 189 - "healthcheck"
Cohesion: 0.29
Nodes (7): interval, retries, start_interval, start_period, test, timeout, healthcheck

### Community 190 - "chat/package.json"
Cohesion: 0.29
Nodes (6): exports, ./package.json, main, name, types, version

### Community 191 - "map/package.json"
Cohesion: 0.29
Nodes (6): exports, ./package.json, main, name, types, version

### Community 192 - "test"
Cohesion: 0.29
Nodes (7): command, cwd, test, cache, executor, options, outputs

### Community 193 - "env.py"
Cohesion: 0.48
Nodes (5): custom_include_object(), do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 194 - "test"
Cohesion: 0.29
Nodes (7): command, cwd, test, cache, executor, options, outputs

### Community 195 - "Tasks"
Cohesion: 0.29
Nodes (6): 1. Dependencies & Configuration, 3. Local Retrieval, 8. Map Integration & App Composition, 9. Integration Verification, Tasks, Workflow follow-up

### Community 196 - "format"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, filePatterns, format

### Community 197 - "lint"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, lintFilePatterns, lint

### Community 199 - "test_chat_contract_fixtures.py"
Cohesion: 0.53
Nodes (3): _load(), test_shared_chat_requests_validate(), test_shared_sse_events_validate_and_round_trip()

### Community 200 - "hermes-api/tests/test_config.py"
Cohesion: 0.53
Nodes (4): _settings(), test_chat_can_be_disabled(), test_settings_load_without_chat_variables(), test_settings_with_chat_variables()

### Community 201 - "@react-router/dev"
Cohesion: 0.33
Nodes (4): @react-router/dev@^8.3.1, @vercel/react-router@^1.3.7, @react-router/dev, @vercel/react-router

### Community 202 - "hermes-e2e/package.json"
Cohesion: 0.33
Nodes (5): name, nx, implicitDependencies, private, version

### Community 203 - "hermes/project.json"
Cohesion: 0.33
Nodes (5): name, projectType, $schema, sourceRoot, tags

### Community 204 - "format"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, filePatterns, format

### Community 205 - "lint"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, lintFilePatterns, lint

### Community 206 - "test_import_isolation.py"
Cohesion: 0.47
Nodes (3): _run(), test_accessing_chat_loads_engine(), test_imports_do_not_load_chat_stack()

### Community 207 - "context"
Cohesion: 0.60
Nodes (6): context, dockerfile, target, build, build, build

### Community 208 - "hermes-worker"
Cohesion: 0.33
Nodes (6): DB_HOST, environment, environment, profiles, volumes, hermes-worker

### Community 209 - "hermes"
Cohesion: 0.33
Nodes (6): HOST, environment, ports, restart, volumes, hermes

### Community 210 - "chat/tsconfig.json"
Cohesion: 0.33
Nodes (5): extends, files, include, ../../tsconfig.base.json, references

### Community 211 - "Mapbox & GIS Standards (`libs/map`)"
Cohesion: 0.33
Nodes (5): 1. WebGL Layer Authoring & Expressions, 2. Coordinate Screen Projection for Overlays, 3. Viewport Debouncing & Bounds Clamping, 4. Camera Motion Physics, Mapbox & GIS Standards (`libs/map`)

### Community 212 - "map/tsconfig.json"
Cohesion: 0.33
Nodes (5): extends, files, include, ../../tsconfig.base.json, references

### Community 213 - "format"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, filePatterns, format

### Community 214 - "lint"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, lintFilePatterns, lint

### Community 215 - "Hermes DB (`libs/shared/hermes-db`)"
Cohesion: 0.33
Nodes (5): 1. Commands, 2. Invariants, 3. Tunables, 4. Domain Triggers, Hermes DB (`libs/shared/hermes-db`)

### Community 216 - "Database Standards"
Cohesion: 0.33
Nodes (5): Database & ORM, Database Standards, Schema Migrations (Alembic), Spatial & PostGIS, Testing

### Community 217 - "format"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, filePatterns, format

### Community 218 - "lint"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, lintFilePatterns, lint

### Community 220 - "util-types/tsconfig.json"
Cohesion: 0.33
Nodes (5): extends, files, include, ../../../tsconfig.base.json, references

### Community 221 - "format"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, filePatterns, format

### Community 222 - "lint"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, lintFilePatterns, lint

### Community 223 - "ts/tsconfig.json"
Cohesion: 0.33
Nodes (5): extends, files, include, ../../../../tsconfig.base.json, references

### Community 224 - "2. Ingestion Adapter Engine"
Cohesion: 0.33
Nodes (5): 1. Database Schema & Source Curation, 2. Ingestion Adapter Engine, 3. Multi-Factor Ranking & AI Triage, 4. Verification & Validation, Tasks

### Community 225 - "hermes-workspace"
Cohesion: 0.60
Nodes (6): hermes-ai, hermes-api, hermes-db, hermes-worker, hermes-workspace, utils-py

### Community 226 - "tsconfig.json"
Cohesion: 0.33
Nodes (5): compileOnSave, extends, files, ./tsconfig.base.json, references

### Community 227 - "Langfuse CI/CD"
Cohesion: 0.40
Nodes (4): Checklist, Common Issues, GitHub specific checklist, Langfuse CI/CD

### Community 228 - "Prompt Engineering"
Cohesion: 0.40
Nodes (4): Adjusting an existing prompt, Model-specific tuning, Prompt Engineering, Universal principles

### Community 229 - "Hermes Application (`apps/hermes`)"
Cohesion: 0.40
Nodes (4): 1. Commands, 2. Invariants, 3. Domain Triggers, Hermes Application (`apps/hermes`)

### Community 230 - "options"
Cohesion: 0.40
Nodes (5): options, args, debug, silent, verbose

### Community 232 - "options"
Cohesion: 0.40
Nodes (5): options, args, debug, silent, verbose

### Community 233 - "path"
Cohesion: 0.60
Nodes (5): path, required, env_file, env_file, env_file

### Community 234 - "options"
Cohesion: 0.40
Nodes (5): options, args, debug, silent, verbose

### Community 235 - "options"
Cohesion: 0.40
Nodes (5): options, args, debug, silent, verbose

### Community 236 - "options"
Cohesion: 0.40
Nodes (5): options, args, debug, silent, verbose

### Community 237 - "Python Standards"
Cohesion: 0.50
Nodes (3): Coding Style & Conventions, Python Standards, Tooling & Logging

### Community 238 - "lock"
Cohesion: 0.50
Nodes (4): executor, options, update, lock

### Community 239 - "lock"
Cohesion: 0.50
Nodes (4): executor, options, update, lock

### Community 240 - "test"
Cohesion: 0.50
Nodes (4): test, cache, executor, outputs

### Community 241 - "services"
Cohesion: 0.50
Nodes (3): services, volumes, hermes_data

### Community 242 - "lock"
Cohesion: 0.50
Nodes (4): executor, options, update, lock

### Community 243 - "lock"
Cohesion: 0.50
Nodes (4): executor, options, update, lock

### Community 244 - "test"
Cohesion: 0.50
Nodes (4): test, cache, executor, outputs

### Community 245 - "lock"
Cohesion: 0.50
Nodes (4): executor, options, update, lock

### Community 247 - "add"
Cohesion: 0.67
Nodes (3): executor, options, add

### Community 248 - "remove"
Cohesion: 0.67
Nodes (3): executor, options, remove

### Community 249 - "sync"
Cohesion: 0.67
Nodes (3): executor, options, sync

### Community 251 - "update"
Cohesion: 0.67
Nodes (3): update, executor, options

### Community 253 - "add"
Cohesion: 0.67
Nodes (3): executor, options, add

### Community 254 - "sync"
Cohesion: 0.67
Nodes (3): executor, options, sync

### Community 255 - "sync"
Cohesion: 0.67
Nodes (3): executor, options, sync

### Community 259 - "add"
Cohesion: 0.67
Nodes (3): executor, options, add

### Community 260 - "sync"
Cohesion: 0.67
Nodes (3): executor, options, sync

## Knowledge Gaps
- **21 isolated node(s):** `../../tsconfig.base.json`, `../../tsconfig.base.json`, `../../tsconfig.base.json`, `../../tsconfig.base.json`, `../../tsconfig.base.json` (+16 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1782 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **65 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `5. API Surface & Guards` connect `chat_guards.py` to `ChatRuntime`, `search.py`, `Tasks`, `chat_retriever.py`, `asyncio`, `use-chat.spec.tsx`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 50 inferred relationships involving `AiConfig` (e.g. with `.__init__()` and `ChatRuntime`) actually correct?**
  _`AiConfig` has 50 INFERRED edges - model-reasoned connections that need verification._
- **What connects `../../tsconfig.base.json`, `../../tsconfig.base.json`, `../../tsconfig.base.json` to the rest of the system?**
  _21 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `search.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06664964249233912 - nodes in this community are weakly interconnected._
- **Why does `ChatStreamEvent` connect `use-chat.spec.tsx` to `chat-store.ts`, `api-types.ts`, `sse.ts`, `chat_guards.py`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `EventService` (e.g. with `Architecture & Boundaries` and `get_event()`) actually correct?**
  _`EventService` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Should `GeocodingService` be split into smaller, more focused modules?**
  _Cohesion score 0.0519219736087206 - nodes in this community are weakly interconnected._