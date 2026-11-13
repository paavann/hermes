# Graph Report - hermes  (2026-11-12)

## Corpus Check
- 430 files · ~196,914 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 34 file(s) not represented in the graph (top: (none) 22, .example 4, .css 2)

## Summary
- 4694 nodes · 9323 edges · 338 communities (235 shown, 103 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 1452 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7d7246bd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sanitization.py
- GeocodingService
- registry.py
- package.json
- pytest
- chat_guards.py
- services/source.py
- DailyTokenBudget
- test_sanitization.py
- api-types.ts
- test_cli.py
- hermes-api
- with
- engine.py
- collections_abc
- llm.py
- core/exceptions.py
- test_chat_prompts.py
- with
- planner.py
- services/source.py
- steps
- .create_event_with_article
- UUID
- ADDED Requirements
- Requirements
- AiConfig
- .stream
- test_chat_web.py
- ChatSource
- EventStatus
- test_chat_service.py
- test_chat_engine.py
- steps
- targets
- react-router
- chat_service.py
- EventService
- react
- cli.py
- util-types/src/index.ts
- env.py
- make_uuid
- ADDED Requirements
- ADDED Requirements
- Requirements
- Requirements
- ChatScope
- What Changes
- ._run_create
- AiService
- react-router
- dependencies
- _extracts_response
- test_chat_planner.py
- auth.tsx
- chat-store.ts
- test_chat_models.py
- nx.json
- compilerOptions
- sse.ts
- SearchService
- services/event.py
- TestEventModel
- Langfuse
- hermes-ai/tests/test_rate_limiter.py
- test_search_service.py
- test_chat_citations.py
- TestEventTlModel
- components.json
- test_event_service.py
- Hermes Web Client (`@hermes/hermes`)
- hermes-worker/tests/test_config.py
- fetch_feed
- map-view.tsx
- GeocodeCacheService
- 17. Known Constraints and Technical Debt
- enumerate_tl_pages
- hermes_ai/__init__.py
- 4. Chat Engine (`hermes-ai`)
- compilerOptions
- TestSourceModel
- 18. Appendix
- React & React Router Standards
- Langfuse Dataset Construction
- use-chat.ts
- Hermes Worker — Architecture & Design Rationale
- Hermes — Production Architecture & System Design
- Tasks
- unittest_mock
- test_chat_api.py
- close_db
- command
- Decisions
- TestCreateArticle
- compilerOptions
- compilerOptions
- DbChatRetriever
- v1/tl.py
- 10. Hybrid Search and Retrieval (`SearchService`)
- TlService
- v1/events.py
- get_db
- Hermes Workspace
- Key Query Specifications
- DueSource
- auth.tsx
- ConcurrencyGuard
- vite
- compilerOptions
- compilerOptions
- ParsedArticle
- ts/package.json
- ADDED Requirements
- use-auth-workflow.ts
- Requirement: Multi-Factor Trending Score Calculation
- openspec-explore/SKILL.md
- chat_retriever.py
- eslint.config.mjs
- entry.server.tsx
- targets
- Hermes DB — Architecture & Design Rationale
- targets
- ArticleService
- _Extraction
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
- Database Standards
- TestBase
- hermes-e2e/tsconfig.json
- hermes/tsconfig.json
- chat/tsconfig.spec.json
- map/tsconfig.spec.json
- TestEventTlStatus
- util-types/package.json
- overrides
- TestModelsPackage
- hermes-api/project.json
- options
- options
- hermes/tsconfig.spec.json
- hermes-worker/project.json
- options
- Hermes REST API (`hermes-api`)
- hermes-ai/project.json
- options
- targets
- hermes-db/project.json
- options
- options
- tl_service.py
- ui-components/tsconfig.json
- ui-components/tsconfig.spec.json
- py/project.json
- options
- targets
- Langfuse v4 project migration
- ChatRuntime
- @playwright/test
- Hermes Frontend Architecture & Rationale
- Hermes Worker
- hermes-api
- ui-components/package.json
- util-types/tsconfig.spec.json
- hello.py
- Proposal
- Judge Calibration
- Langfuse Prompt Migration
- clerk-proxy.ts
- @react-router/dev
- hermes/package.json
- healthcheck
- chat/package.json
- map/package.json
- test
- test
- Hermes API — Architecture & Design Rationale
- format
- lint
- Backend & FastAPI Standards
- @eslint/js@^9.8.0
- Hermes Map (`libs/map`)
- hermes-e2e/package.json
- hermes/project.json
- format
- lint
- @nx/eslint@23.2.1
- context
- hermes-worker
- hermes
- chat/tsconfig.json
- map/tsconfig.json
- format
- lint
- Hermes DB (`libs/shared/hermes-db`)
- format
- lint
- TestGeocodeCacheModel
- util-types/tsconfig.json
- format
- lint
- ts/tsconfig.json
- TypeScript & Frontend Standards
- hermes-workspace
- tsconfig.json
- Langfuse CI/CD
- Prompt Engineering
- Hermes Application (`apps/hermes`)
- options
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
- update
- add
- sync
- sync
- @nx/web@23.2.1
- _Mappings
- add
- sync
- explanations.md
- db.py
- shadcn@^4.21.5
- _sort_timeline_titles
- @types/react-dom@^19.0.0
- EventTl
- 16. Change Playbooks and Tunables
- init_db
- SearchFilters
- @swc/helpers@~0.5.18

## God Nodes (most connected - your core abstractions)
1. `EventService` - 73 edges
2. `run()` - 69 edges
3. `AiConfig` - 66 edges
4. `LlmService` - 56 edges
5. `react` - 48 edges
6. `GeocodingService` - 42 edges
7. `SearchService` - 42 edges
8. `make_uuid()` - 38 edges
9. `TbRateLimiter` - 37 edges
10. `ModelRoute` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Step-by-Step Processing Stages` --references--> `GeocodingService`  [INFERRED]
  apps/hermes-api/docs/architecture.md → libs/shared/hermes-ai/src/hermes_ai/services/geocoding.py
- `Architectural Optimizations ("The Why")` --references--> `GeocodingService`  [INFERRED]
  docs/architecture.md → libs/shared/hermes-ai/src/hermes_ai/services/geocoding.py
- `Defense Mechanisms` --references--> `NominatimResilienceManager`  [INFERRED]
  apps/hermes-worker/docs/architecture.md → libs/shared/hermes-ai/src/hermes_ai/services/geocoding.py
- `Risks / Trade-offs` --references--> `SitemapFetcher`  [INFERRED]
  openspec/changes/archive/2026-10-20-multi-source-ingestion-and-ranking/design.md → apps/hermes-worker/src/hermes_worker/services/fetchers/sitemap.py
- `1. Package boundaries and lazy loading` --references--> `ChatRetriever`  [INFERRED]
  openspec/changes/archive/2026-11-09-add-conversational-rag/design.md → libs/shared/hermes-ai/src/hermes_ai/chat/retriever.py

## Import Cycles
- None detected.

## Communities (338 total, 103 thin omitted)

### Community 0 - "sanitization.py"
Cohesion: 0.06
Nodes (23): Architectural Decisions ("The Why"), Observability & Tracing (Langfuse), LLM Observability & Tracing (Langfuse), Observability & Langfuse Integration, _build_events_prompt(), _reidx_results(), clean_invisible_chars(), clean_xml_text() (+15 more)

### Community 1 - "GeocodingService"
Cohesion: 0.05
Nodes (38): mock_cache_service(), TestGeocodingService, run(), run(), run(), run(), run(), run() (+30 more)

### Community 2 - "registry.py"
Cohesion: 0.08
Nodes (17): _article_source(), _build_event_evidence(), _build_timeline_evidence(), CitationRegistry, _event_source(), _normalize_marker(), _parse_date(), _timeline_source() (+9 more)

### Community 3 - "package.json"
Cohesion: 0.04
Nodes (78): devDependencies, autoprefixer@^10.5.4, @babel/core@^7.14.5, @babel/preset-react@^7.14.5, eslint@^9.8.0, eslint-config-prettier@^10.0.0, eslint-plugin-import@2.31.0, eslint-plugin-jsx-a11y@6.10.1 (+70 more)

### Community 4 - "pytest"
Cohesion: 0.09
Nodes (16): test_event_scope_requires_event_id(), test_request_rejects_bad_role(), test_request_rejects_more_than_sixteen_messages(), test_request_rejects_oversized_message_and_history_content(), test_request_requires_message(), test_request_strips_and_rejects_blank_message(), _config(), DummyRetriever (+8 more)

### Community 5 - "chat_guards.py"
Cohesion: 0.09
Nodes (13): ChatGuards, extract_client_ip(), hash_client_ip(), SlidingWindowRateLimiter, FakeClock, _guards(), _request(), test_chat_guards_hash_client_key_and_rate_limit() (+5 more)

### Community 6 - "services/source.py"
Cohesion: 0.08
Nodes (22): 11.4 Concurrency and race conditions, ADR-13: Naive UTC timestamps, _load_sources_config(), SourceService, sync_sources_from_config(), _make_source(), _mock_session(), test_load_sources_config_file_not_found() (+14 more)

### Community 7 - "DailyTokenBudget"
Cohesion: 0.16
Nodes (6): BudgetReservation, DailyTokenBudget, test_budget_reconciliation_records_actual_usage_once(), test_budget_rejects_and_resets_at_utc_midnight(), test_budget_reservation_release_frees_the_estimate(), test_budget_zero_disables_accounting()

### Community 8 - "test_sanitization.py"
Cohesion: 0.13
Nodes (7): Architectural Decisions ("The Why"), create_ai_client(), TestWorkerAiClientFactory, run(), run(), run(), run()

### Community 9 - "api-types.ts"
Cohesion: 0.05
Nodes (37): ChatState, ArticleResponse, ChatCoverage, ChatCoverageLevel, ChatDegradedFlag, ChatDone, ChatDoneEvent, ChatError (+29 more)

### Community 10 - "test_cli.py"
Cohesion: 0.13
Nodes (15): handle_all(), handle_lifecycle(), handle_sync(), WorkerCmd, build_parser(), run_lifecycle(), test_build_parser_commands(), test_handle_all() (+7 more)

### Community 11 - "hermes-api"
Cohesion: 0.06
Nodes (47): context, dockerfile, target, resources, path, required, ENV, HOST (+39 more)

### Community 12 - "with"
Cohesion: 0.04
Nodes (46): concurrency, cancel-in-progress, group, if, name, needs, secrets, uses (+38 more)

### Community 13 - "engine.py"
Cohesion: 0.20
Nodes (17): _provenance(), ChatStage, ChatUsage, DoneEvent, ErrorCode, ErrorEvent, Provenance, SourcesEvent (+9 more)

### Community 14 - "collections_abc"
Cohesion: 0.07
Nodes (15): downgrade(), upgrade(), downgrade(), upgrade(), downgrade(), upgrade(), upgrade(), downgrade() (+7 more)

### Community 15 - "llm.py"
Cohesion: 0.14
Nodes (10): configure_langfuse(), flush_langfuse(), _is_content_attribute(), mask_otel_spans(), _build_deployments(), _deployment(), _fallback_alias(), test_mask_otel_spans_deletes_content_but_keeps_operational_attributes() (+2 more)

### Community 16 - "core/exceptions.py"
Cohesion: 0.08
Nodes (19): _cors_headers(), register_err_handlers(), app_exception_handler(), http_exception_handler(), universal_exception_handler(), validation_exception_handler(), AppException, ChatBudgetExhausted (+11 more)

### Community 17 - "test_chat_prompts.py"
Cohesion: 0.14
Nodes (15): WebResult, build_answer_messages(), format_evidence(), _iso(), _tag(), test_web_result_caps_title_and_snippet(), test_answer_messages_include_rules_scope_and_question(), test_answer_messages_note_unavailable_web() (+7 more)

### Community 18 - "with"
Cohesion: 0.05
Nodes (40): if, name, needs, runs-on, steps, name, outputs, runs-on (+32 more)

### Community 19 - "planner.py"
Cohesion: 0.05
Nodes (24): ChatPlanner, PlannerOutcome, PlanRunner, render_history(), ConfigurationError, test_render_history_is_empty_without_turns(), DummyCache, DummyCacheEntry (+16 more)

### Community 20 - "services/source.py"
Cohesion: 0.09
Nodes (12): _extract_domain(), _parse_gdelt_date(), _extract_article_from_html(), _parse_sitemap_urls(), test_extract_article_from_html(), test_extract_domain(), test_parse_gdelt_date(), test_parse_sitemap_urls() (+4 more)

### Community 21 - "steps"
Cohesion: 0.06
Nodes (39): name, outputs, runs-on, steps, concurrency, cancel-in-progress, group, if (+31 more)

### Community 22 - ".create_event_with_article"
Cohesion: 0.09
Nodes (27): 13.3 Fixtures and factories, 13.5 SQL and migration-consistency assertions, 17.10 Read-modify-write scoring is race-prone, 17.13 Lazy relationships raise `MissingGreenlet`, 17.16 `category_color` is optional in the protocol, non-null in the schema, 17.5 STALE is reactivated by corroboration; ARCHIVED is terminal, 17.6 `article_count` is incremented, never recomputed, 2.2 Structural typing at the AI boundary (+19 more)

### Community 23 - "UUID"
Cohesion: 0.13
Nodes (5): test_get_event_detail_not_found(), test_get_event_detail_success(), test_get_events_by_bbox_success(), test_get_events_with_scope_parameter(), test_tl_endpoint_post()

### Community 24 - "ADDED Requirements"
Cohesion: 0.05
Nodes (38): ADDED Requirements, Purpose, Requirement: Bounded web search escalation, Requirement: Citation-bearing current-affairs claims, Requirement: Citation validation and provenance, Requirement: Explicit background knowledge labeling, Requirement: External evidence disclosure, Requirement: Planner-driven retrieval query (+30 more)

### Community 25 - "Requirements"
Cohesion: 0.05
Nodes (38): Conversational RAG Specification, Purpose, Requirement: Bounded web search escalation, Requirement: Citation-bearing current-affairs claims, Requirement: Citation validation and provenance, Requirement: Explicit background knowledge labeling, Requirement: External evidence disclosure, Requirement: Planner-driven retrieval query (+30 more)

### Community 26 - "AiConfig"
Cohesion: 0.09
Nodes (49): HermesAi, AiConfig, ModelRoute, ModelTarget, EventExtractor, _clean_json_str(), LlmService, _config() (+41 more)

### Community 27 - ".stream"
Cohesion: 0.11
Nodes (8): AnswerModel, ChatEngine, _chunk_text(), _close_stream(), _int(), _merge_usage(), Planner, WebSearcher

### Community 28 - "test_chat_web.py"
Cohesion: 0.09
Nodes (30): _as_float(), parse_published_at(), sanitize_text(), source_name_from_url(), TavilyTool, validated_url(), WebSearchOutcome, WebSearchService (+22 more)

### Community 29 - "ChatSource"
Cohesion: 0.12
Nodes (29): citationClass(), CitationKind, CitationMarkerSegment, CitationRenderOptions, CitationSegment, CitationTextSegment, citationTitle(), CLICKABLE_CLASS (+21 more)

### Community 30 - "EventStatus"
Cohesion: 0.07
Nodes (18): test_rss_fetcher_missing_feed_url(), test_sitemap_fetcher_rate_limited_or_forbidden(), test_sitemap_fetcher_success(), dummy_due_source(), 5.3 Enumerations, ADR-10: Enums persisted as uppercase names, mostly native PostgreSQL types, CredibilityTier, EventScope (+10 more)

### Community 31 - "test_chat_service.py"
Cohesion: 0.12
Nodes (30): _done(), FakeEngine, FakeRequest, FakeRuntime, _frames(), _guards(), _service(), _source() (+22 more)

### Community 32 - "test_chat_engine.py"
Cohesion: 0.17
Nodes (23): _collect(), _config(), _engine(), _event(), FakeAnswer, FakePlanner, FakeRetriever, FakeWeb (+15 more)

### Community 33 - "steps"
Cohesion: 0.06
Nodes (33): name, outputs, runs-on, steps, concurrency, cancel-in-progress, group, if (+25 more)

### Community 34 - "targets"
Cohesion: 0.07
Nodes (33): executor, options, executor, options, executor, options, executor, options (+25 more)

### Community 35 - "react-router"
Cohesion: 0.10
Nodes (20): CapabilitiesSection(), CAPABILITY_CARDS, Footer(), HeroSection(), LaunchMapBtn(), LaunchMapBtnProps, Nav(), NAV_ITEMS (+12 more)

### Community 36 - "chat_service.py"
Cohesion: 0.11
Nodes (24): ChatBoundingBox, ChatCoverage, ChatDone, ChatDoneEvent, ChatError, ChatErrorEvent, ChatEventScope, ChatGlobalScope (+16 more)

### Community 37 - "EventService"
Cohesion: 0.11
Nodes (9): 17.9 Status eligibility is inconsistent across read paths, 9.5 `EventService` — read operations, ADR-04: Read paths project directly to DTOs, EventService, make_async_session(), TestArticleUrlExistsDelegation, TestGetActiveEvents, TestGetActiveEventsByEmbeddings (+1 more)

### Community 38 - "react"
Cohesion: 0.13
Nodes (16): Button(), ButtonProps, buttonVariants, InputProps, LabelProps, SeparatorProps, TextareaProps, BootSequenceProps (+8 more)

### Community 39 - "cli.py"
Cohesion: 0.11
Nodes (12): main(), run_app(), setup_logging(), test_main(), test_run_app_exception(), _test(), test_run_app_missing_handler(), _test() (+4 more)

### Community 40 - "util-types/src/index.ts"
Cohesion: 0.12
Nodes (16): 3. Monorepo UI Architecture & Strict shadcn Discipline, citedEventsFromSources(), DynamicMapContainer, HydrateFallback(), loader(), MAP_CONFIG, MapLoadingFallback(), MapRoute() (+8 more)

### Community 41 - "env.py"
Cohesion: 0.18
Nodes (6): custom_include_object(), do_run_migrations(), _get_migration_db_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 42 - "make_uuid"
Cohesion: 0.10
Nodes (9): make_article(), make_event(), make_source(), make_uuid(), utcnow(), session_url_exists(), TestAddArticleToEvent, _flush() (+1 more)

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
Cohesion: 0.12
Nodes (13): fake_search_service(), FakeEmbeddingClient, FakeSearchService, FakeSession, _result(), _retriever(), factory(), test_embedding_failure_falls_back_to_lexical_search() (+5 more)

### Community 48 - "What Changes"
Cohesion: 0.15
Nodes (12): Capabilities, Conversational interface, Deferred, Grounded answer pipeline, Impact, Local retrieval, Modified Capabilities, New Capabilities (+4 more)

### Community 50 - "AiService"
Cohesion: 0.07
Nodes (21): 1. Commands, 2. Invariants, 3. Domain Triggers, Hermes API (`apps/hermes-api`), get_settings(), Settings, setup_logging(), index() (+13 more)

### Community 51 - "react-router"
Cohesion: 0.23
Nodes (8): PrivacyNav(), PRIVACY_SECTIONS, PrivacyPolicyContent(), PrivacySection, meta(), PrivacyRoute(), @clerk/react-router, react-router

### Community 52 - "dependencies"
Cohesion: 0.07
Nodes (30): dependencies, axios@^1.20.0, @base-ui/react@^1.9.0, class-variance-authority@^0.7.1, @clerk/react-router@^3.6.35, clsx@^2.1.1, cn@^0.4.0, @fontsource-variable/jetbrains-mono@^5.3.0 (+22 more)

### Community 53 - "_extracts_response"
Cohesion: 0.09
Nodes (8): _extracts_response(), _mock_httpx_response(), _page(), TestEdgeCases, counting_get(), TestFetchPageExtracts, counting_get(), counting_get()

### Community 54 - "test_chat_planner.py"
Cohesion: 0.09
Nodes (21): fallback_plan(), _planner(), test_event_scope_is_rendered_in_prompt(), run(), test_fallback_plan_is_never_blank(), test_fallback_plan_strips_invisible_characters(), test_planner_drops_unknown_category(), run() (+13 more)

### Community 55 - "auth.tsx"
Cohesion: 0.17
Nodes (21): AuthCheckerboardPattern(), computeCheckerboardLayout(), EmailStep(), OtpStepProps, PasswordStep(), PasswordStepProps, SetupStep(), SetupStepProps (+13 more)

### Community 56 - "chat-store.ts"
Cohesion: 0.12
Nodes (19): Citations, Composition, @hermes/chat, Scope contract, Store, Testing, assistantMessage(), buildHistory() (+11 more)

### Community 57 - "test_chat_models.py"
Cohesion: 0.07
Nodes (20): ChatPlan, PlanTimeRange, ChatTurn, sanitize_history(), test_bounding_box_rejects_inverted_latitudes(), test_bounding_box_rejects_out_of_range_latitudes(), test_bounding_box_rejects_out_of_range_longitudes(), test_chat_plan_drops_blank_optional_fields() (+12 more)

### Community 58 - "nx.json"
Cohesion: 0.08
Nodes (23): analytics, babel, bundler, linter, style, style, generators, @nx/react (+15 more)

### Community 59 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, composite, customConditions, declarationMap, emitDeclarationOnly, importHelpers, isolatedModules, lib (+15 more)

### Community 60 - "sse.ts"
Cohesion: 0.12
Nodes (28): Transport, chatErrorFromTransport(), ChatTransportError, ChatTransportErrorInit, decodeEvent(), ERROR_CODES, ErrorEnvelope, EVENT_TYPES (+20 more)

### Community 61 - "SearchService"
Cohesion: 0.20
Nodes (14): _event(), 10.10 Context hydration, 10.2 Scopes, 17.22 Event-scope search always reports THIN coverage, classify_coverage(), Coverage, SearchArticle, SearchEvent (+6 more)

### Community 62 - "services/event.py"
Cohesion: 0.16
Nodes (15): Key Architectural Decisions ("The Why"), Architecture & Boundaries, 16.3 Adding a table, 5.2 Base classes and mixins, Base, TimestampMixin, UUIDPrimaryKeyMixin, EventTlStatus (+7 more)

### Community 64 - "Langfuse"
Cohesion: 0.09
Nodes (19): Credentials, Discovery, Install, Langfuse CLI Reference, Tips, Skill Feedback, Submission options, 1. Langfuse API via CLI (+11 more)

### Community 65 - "hermes-ai/tests/test_rate_limiter.py"
Cohesion: 0.08
Nodes (20): test_rate_limiter_allows_burst_up_to_limit(), _run(), test_rate_limiter_property(), test_rate_limiter_refills_over_time(), _run(), test_rate_limiter_throttles_after_burst(), _run(), test_rate_limiter_acquire() (+12 more)

### Community 66 - "test_search_service.py"
Cohesion: 0.13
Nodes (30): 13.4 Session doubles: two styles, CoverageLevel, reciprocal_rank_fusion(), _build(), _event_row(), _Result, _search_event(), _service() (+22 more)

### Community 67 - "test_chat_citations.py"
Cohesion: 0.26
Nodes (12): _registry(), test_finalize_answer_filters_unknown_ids_and_tracks_background(), test_finalize_answer_reports_no_citations(), test_registry_assigns_stable_markers_in_order(), test_registry_resolves_sources_with_parent_coordinates(), test_sources_for_deduplicates_in_first_citation_order(), test_stream_filter_drops_unknown_markers_but_keeps_known_ones(), test_stream_filter_flushes_incomplete_marker() (+4 more)

### Community 69 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 70 - "test_event_service.py"
Cohesion: 0.08
Nodes (13): GeopoliticalBloc, calculate_shannon_diversity(), calculate_velocity(), calculate_velocity_multiplier(), boost_multiplier(), _patch_article_create(), TestCalculateShannonDiversity, TestCalculateVelocity (+5 more)

### Community 71 - "Hermes Web Client (`@hermes/hermes`)"
Cohesion: 0.18
Nodes (9): 1. Server-Side Access Control, 2. Client-Only WebGL Dynamic Boundary, Architecture & Responsibilities, Development Commands, Environment Configuration, Hermes Web Client (`@hermes/hermes`), Route Structure, Server-Side Rendering (SSR) & WebGL Isolation (+1 more)

### Community 72 - "hermes-worker/tests/test_config.py"
Cohesion: 0.15
Nodes (6): get_settings(), Settings, _make_settings(), TestGetSettings, TestWorkerDbUrl, TestWorkerSettingsDefaults

### Community 73 - "fetch_feed"
Cohesion: 0.12
Nodes (9): _extract_content(), fetch_feed(), _parse_date(), TestFetchFeed, run(), run(), run(), run() (+1 more)

### Community 74 - "map-view.tsx"
Cohesion: 0.08
Nodes (38): 1. WebGL Layer Authoring & Expressions, 2. Coordinate Screen Projection for Overlays, 3. Viewport Debouncing & Bounds Clamping, 4. Camera Motion Physics, 5. Spatial Deduplication Conventions, Mapbox & GIS Standards (`libs/map`), MapConfig, MapConfigContext (+30 more)

### Community 75 - "GeocodeCacheService"
Cohesion: 0.20
Nodes (4): GeocodeCacheEntry, GeocodeCacheService, TestGetByLocationName, TestSaveGeocodeResult

### Community 76 - "17. Known Constraints and Technical Debt"
Cohesion: 0.10
Nodes (20): 17.11 No optimistic locking or version column, 17.12 Service-level commits prevent composition, 17.14 `EventTlStatus` model and migration disagree, 17.15 Server defaults drift between model and migrations, 17.17 `Article.thumbnail_url` is never populated, 17.19 Source sync cannot clear a field with `null`, 17.1 Import-time settings make `DB_PASSWORD` mandatory for any import, 17.20 Geocode cache is first-write-wins, including failures (+12 more)

### Community 78 - "hermes_ai/__init__.py"
Cohesion: 0.05
Nodes (26): TestAiHelpers, TestExtractedEventModel, run(), run(), CircuitBreakerOpenError, GeocodingError, HermesAiError, ModelExecutionError (+18 more)

### Community 79 - "4. Chat Engine (`hermes-ai`)"
Cohesion: 0.29
Nodes (11): _article(), _evidence(), _timeline(), RetrievedArticle, RetrievedEvidence, RetrievedTimeline, RetrievedTimelineEdge, RetrievedTimelineNode (+3 more)

### Community 81 - "compilerOptions"
Cohesion: 0.11
Nodes (17): compilerOptions, allowJs, esModuleInterop, forceConsistentCasingInFileNames, jsx, lib, outDir, resolveJsonModule (+9 more)

### Community 84 - "18. Appendix"
Cohesion: 0.25
Nodes (8): 18.1 At a glance, 18.2 Index and constraint catalogue, 18.3 Formula reference, 18.4 Source file map, 18.5 Command reference, 18.6 Glossary, 18.7 Verification status, 18. Appendix

### Community 85 - "React & React Router Standards"
Cohesion: 0.08
Nodes (19): 1. Official Documentation Mandate, 2. Directory Structure & The 80/20 Shell Doctrine, 4. Tailwind CSS v4 & Tactical Styling Discipline, 5. Modern React 19 Paradigms, 6. The "You Might Not Need an Effect" Doctrine, 7. The 6-Tier State Management Hierarchy, 8. Tactical GIS & Mapbox Architecture, 9. Component Hygiene & Render Purity (+11 more)

### Community 86 - "Langfuse Dataset Construction"
Cohesion: 0.12
Nodes (13): Critical Rules, Langfuse Dataset Construction, Primary Guide, Workflow, 1. Determine Online or Offline, 2. Establish the Metric Set, 3. Implement and Verify, Setting up evals (+5 more)

### Community 87 - "use-chat.ts"
Cohesion: 0.05
Nodes (53): 7. Conversational RAG UI & Map Integration, Citation Focus, Composition, Highlight Lifecycle, Scope Resolution, MapChat(), MapChatProps, ChatConfig (+45 more)

### Community 88 - "Hermes Worker — Architecture & Design Rationale"
Cohesion: 0.20
Nodes (10): 2. Ingestion Pipeline & Token Optimization, 3. The Grounded Geocoding Shield, 4. Multi-Factor Scoring & Consensus Formulation, 5. Lifecycle Decay & Status Transitions, 6. Observability & Langfuse Tracing, A. Embed Before Extract (Vector Pre-Filtering), Architectural Decisions ("The Why"), B. Bounded Batch Sizing & Memory Limits (+2 more)

### Community 89 - "Hermes — Production Architecture & System Design"
Cohesion: 0.11
Nodes (18): 1. High-Level Production Topology, 2. Infrastructure & Hosting Topology, 3. Data Ingestion & Consensus Pipeline, 4. Multi-Factor Trending & Ranking Algorithm, 5. Spatial Query & WebGL Viewport Synchronization, 6. Causality Timeline Synthesis Engine, 7. Model Routing, Failover & Geocoding Resiliency, 9. CI/CD & Deployment Workflows (+10 more)

### Community 90 - "Tasks"
Cohesion: 0.40
Nodes (4): 1. Database Schema & Source Curation, 3. Multi-Factor Ranking & AI Triage, 4. Verification & Validation, Tasks

### Community 91 - "unittest_mock"
Cohesion: 0.14
Nodes (8): SyncService, _process_source(), TestSyncService, run(), run(), run(), run(), run()

### Community 92 - "test_chat_api.py"
Cohesion: 0.24
Nodes (7): _app(), FakeChatService, test_chat_route_is_503_when_runtime_is_missing(), test_chat_route_rejects_invalid_body_with_422(), test_chat_route_rejects_malformed_bbox(), test_chat_route_returns_429_with_retry_after(), test_chat_route_streams_events_in_order()

### Community 93 - "close_db"
Cohesion: 0.13
Nodes (15): 1. Cloud Infrastructure & Ephemeral Execution Model, Architectural Rationale: Why Ephemeral Compute?, Architecture Topology, Lifecycle of an Ephemeral Execution, Key Architectural Invariants, db_lifespan(), test_db_lifespan(), _test() (+7 more)

### Community 94 - "command"
Cohesion: 0.17
Nodes (15): command, cwd, executor, options, executor, executor, options, options (+7 more)

### Community 95 - "Decisions"
Cohesion: 0.18
Nodes (10): 2. Shannon Diversity Entropy Across 5 Geopolitical Blocs, 3. Submodular Diminishing Returns for Syndicated Wires, 4. Zero-Overhead Severity Triage in LLM Extraction, 5. Continuous Exponential Half-Life Decay, Context, Decisions, Design, Goals / Non-Goals (+2 more)

### Community 96 - "TestCreateArticle"
Cohesion: 0.12
Nodes (3): run(), TestCreateArticle, TestRunLifecycleTransitions

### Community 97 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, emitDeclarationOnly, forceConsistentCasingInFileNames, module, moduleResolution, outDir, rootDir, tsBuildInfoFile (+6 more)

### Community 98 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, emitDeclarationOnly, forceConsistentCasingInFileNames, module, moduleResolution, outDir, rootDir, tsBuildInfoFile (+6 more)

### Community 99 - "DbChatRetriever"
Cohesion: 0.18
Nodes (7): 4. Conversational RAG Pipeline (`POST /api/v1/chat`), Guards and Kill Switch, Scope Resolution & Retrieval, SSE Contract, DbChatRetriever, EmbeddingClient, Migration Plan

### Community 100 - "v1/tl.py"
Cohesion: 0.14
Nodes (3): analyze_event_tl(), get_tl_service(), ErrorResponseSchema

### Community 101 - "10. Hybrid Search and Retrieval (`SearchService`)"
Cohesion: 0.11
Nodes (17): 10.11 Relaxed retry and degradation, 10.12 Defensive row mapping, 10.13 Search design notes, 10.1 Public result model, 10.3 Eligibility conditions, 10.4 Query pipeline, 10.5 Lexical CTE, 10.6 Semantic CTE (+9 more)

### Community 102 - "TlService"
Cohesion: 0.23
Nodes (16): TlResponse, TlService, dummy_event(), mock_ai_extraction(), mock_geocoding(), mock_tl_db(), test_concurrent_generation_returns_generating(), run_test() (+8 more)

### Community 103 - "v1/events.py"
Cohesion: 0.24
Nodes (10): get_event(), get_event_service(), get_events(), get_events_by_bbox(), ArticleResponse, EventDetailResponse, EventResponse, MapEventResponse (+2 more)

### Community 104 - "get_db"
Cohesion: 0.12
Nodes (12): 13.1 Philosophy: unit tests, no database, 13.2 Import isolation, 13.6 Test module map, 13.7 What the suite does not test, 13.8 Coverage and reporting, 13. Testing Architecture, ADR-02: The library owns models and services; consumers own sessions, get_db() (+4 more)

### Community 106 - "Hermes Workspace"
Cohesion: 0.15
Nodes (12): 1. Commands, 2. Invariants, 3. Conventions, 4. Gotchas & Landmines, 5. Boundaries & Environment, 6. Domain Triggers, AWS Guidance for the new AWS experience, Constraints: (+4 more)

### Community 107 - "Key Query Specifications"
Cohesion: 0.18
Nodes (11): 1. Spatial Viewport Bounding Box (`GET /api/v1/events/bbox`), 2. Event List Query (`GET /api/v1/events/`), 3. On-Demand Timeline Synthesis (`POST /api/v1/events/tl/{event_id}`), 4. Conversational Chat (`POST /api/v1/chat`), Configuration & Environment Variables, Development Runbook, Endpoints Overview, Hermes REST API (`hermes-api`) (+3 more)

### Community 108 - "DueSource"
Cohesion: 0.15
Nodes (19): BaseArticleFetcher, GDELTFetcher, RSSFetcher, SitemapFetcher, test_gdelt_fetcher_malformed_json(), _run(), test_gdelt_fetcher_rate_limit_circuit_breaker(), _run() (+11 more)

### Community 109 - "auth.tsx"
Cohesion: 0.25
Nodes (7): OtpStep(), SsoCallbackView(), Auth(), mockSetActive, mockSignIn, mockSignUp, HermesWordmark()

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

### Community 114 - "ParsedArticle"
Cohesion: 0.22
Nodes (3): ParsedArticle, _truncate_to_words(), TestParsedArticleModel

### Community 115 - "ts/package.json"
Cohesion: 0.15
Nodes (12): dependencies, exports, ./package.json, main, name, nx, name, tags (+4 more)

### Community 116 - "ADDED Requirements"
Cohesion: 0.15
Nodes (12): ADDED Requirements, Purpose, Requirement: Continuous Half-Life Decay, Requirement: Multi-Factor Trending Score Calculation, Requirement: Real-World Severity Classification, Scenario: Breaking velocity boost, Scenario: Critical global crisis classification, Scenario: Cross-border consensus amplification (+4 more)

### Community 117 - "use-auth-workflow.ts"
Cohesion: 0.33
Nodes (7): EmailStepProps, AuthMode, extractClerkError(), OAUTH_STRATEGY_MAP, useAuthWorkflow(), UseAuthWorkflowReturn, OAuthProviderId

### Community 118 - "Requirement: Multi-Factor Trending Score Calculation"
Cohesion: 0.15
Nodes (12): Event Ranking Specification, Purpose, Requirement: Continuous Half-Life Decay, Requirement: Multi-Factor Trending Score Calculation, Requirement: Real-World Severity Classification, Requirements, Scenario: Breaking velocity boost, Scenario: Critical global crisis classification (+4 more)

### Community 119 - "openspec-explore/SKILL.md"
Cohesion: 0.17
Nodes (11): Check for context, Ending Discovery, Guardrails, Handling Different Entry Points, OpenSpec Awareness, Planning a Change, The Stance, What You Don't Have To Do (+3 more)

### Community 120 - "chat_retriever.py"
Cohesion: 0.09
Nodes (12): _plan_filters(), RetrievalFilters, RetrievalResult, ChatRetriever, FakeRetriever, _result(), test_chat_retriever_module_does_not_import_hermes_db(), test_fake_retriever_conforms_to_protocol() (+4 more)

### Community 122 - "eslint.config.mjs"
Cohesion: 0.23
Nodes (4): eslint-plugin-playwright@^1.6.2, @nx/eslint-plugin@23.2.1, eslint-plugin-playwright, @nx/eslint-plugin

### Community 123 - "entry.server.tsx"
Cohesion: 0.20
Nodes (7): streamTimeout, isbot@^4.4.0, react-dom@^19.2.8, @react-router/node@^8.3.1, isbot, react-dom, @react-router/node

### Community 124 - "targets"
Cohesion: 0.17
Nodes (12): executor, options, executor, executor, options, executor, options, targets (+4 more)

### Community 125 - "Hermes DB — Architecture & Design Rationale"
Cohesion: 0.06
Nodes (33): 12.1 Environment wiring, 12.2 Revision chain, 12.3 Migration patterns used here, 12.4 Model ↔ migration drift watchlist, 12.5 Operational migration rules, 12. Migration Architecture (Alembic), 15. Design Decisions (ADR Summary), 2.1 Why a shared library instead of per-app models (+25 more)

### Community 126 - "targets"
Cohesion: 0.17
Nodes (12): executor, options, executor, executor, options, targets, add, install (+4 more)

### Community 127 - "ArticleService"
Cohesion: 0.14
Nodes (7): 9.1 `ArticleService`, 9.3 `EventService` — corroboration and scoring, 9.4 Ranking primitives (`services/ranking.py`), 9.8 `GeocodeCacheService`, 9. Service Layer, ArticleService, TestArticleUrlExists

### Community 128 - "_Extraction"
Cohesion: 0.27
Nodes (3): _Extraction, _Geocoding, TestEventCreationNormalization

### Community 130 - "Decisions"
Cohesion: 0.11
Nodes (18): 10. SSE API contract and lifecycle, 12. Observability and privacy, 13. Frontend chat library and state, 14. Map integration and highlighting, 1. Package boundaries and lazy loading, 2. LangChain as orchestration, LiteLLM Router as transport, 4. Hybrid retrieval and reciprocal rank fusion, 5. Scope, eligibility, filters, and coverage (+10 more)

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
Cohesion: 0.16
Nodes (7): _load(), test_shared_chat_requests_validate(), test_shared_sse_events_validate_and_round_trip(), _index_expression(), _load_migration(), test_fts_index_registered_in_metadata(), test_metadata_expression_matches_migration()

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

### Community 145 - "Database Standards"
Cohesion: 0.33
Nodes (5): Database & ORM, Database Standards, Schema Migrations (Alembic), Spatial & PostGIS, Testing

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

### Community 161 - "Hermes REST API (`hermes-api`)"
Cohesion: 0.15
Nodes (7): CLI Commands & Targets, Configuration & Environment Variables, Development Runbook, Hermes Ingestion & Lifecycle Worker (`hermes-worker`), Ingestion Pipeline Stages, Observability & Tracing (Langfuse), Operational Model & Cloud Topology

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

### Community 168 - "tl_service.py"
Cohesion: 0.11
Nodes (11): EventNotFoundException, TlGenErr, WikiSearchException, _fetch_extracts_batch(), fetch_page_extracts(), search_timeline_titles(), search_wikipedia(), _search_response() (+3 more)

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

### Community 175 - "ChatRuntime"
Cohesion: 0.08
Nodes (12): create_chat_stream(), get_chat_service(), estimate_tokens(), ChatRuntime, ChatService, _engine_scope(), _history_turn(), PreparedTurn (+4 more)

### Community 176 - "@playwright/test"
Cohesion: 0.25
Nodes (6): @nx/devkit@23.2.1, @nx/playwright@23.2.1, @playwright/test@^1.37.0, @nx/devkit, @nx/playwright, @playwright/test

### Community 177 - "Hermes Frontend Architecture & Rationale"
Cohesion: 0.14
Nodes (14): 1. Application Role & Architecture Boundary, 2. Server-Side Rendering (`ssr: true`) & Authentication Guarding, 3. WebGL Canvas Isolation & SSR Boundary Analysis, 4. Map Rendering & Interaction Boundaries, 5. Design System Integration, 6. Provider Composition & Data Boundaries, 8. Production Hosting & Network Topology, Authentication Guarding (+6 more)

### Community 178 - "Hermes Worker"
Cohesion: 0.25
Nodes (7): 1. Commands, 2. Boundaries, 3. Invariants, 4. Runtime & Memory, 5. Tunables, 6. Triggers, Hermes Worker

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
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, Proposal, Why

### Community 184 - "Judge Calibration"
Cohesion: 0.29
Nodes (6): 1. Prepare the calibration, 2. Run the calibration, 3. Review the results, 4. Iterate until the judge is approved, 5. Deploy the approved judge, Judge Calibration

### Community 185 - "Langfuse Prompt Migration"
Cohesion: 0.29
Nodes (6): 1. Inventory every prompt (before writing any code), 2. Convert templating and decide structure, 3. Present the plan, then create and refactor, 4. Verify, Langfuse Prompt Migration, Prerequisites

### Community 186 - "clerk-proxy.ts"
Cohesion: 0.38
Nodes (5): Frontend & React Standards, TanStack Query Best Practices, action(), handleClerkProxy(), loader()

### Community 187 - "@react-router/dev"
Cohesion: 0.33
Nodes (4): @react-router/dev@^8.3.1, @vercel/react-router@^1.3.7, @react-router/dev, @vercel/react-router

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

### Community 194 - "test"
Cohesion: 0.29
Nodes (7): command, cwd, test, cache, executor, options, outputs

### Community 195 - "Hermes API — Architecture & Design Rationale"
Cohesion: 0.13
Nodes (15): 1. Application Role & Architectural Boundaries, 2. Spatial Viewport Query Pipeline, 3. Timeline Engine Orchestration Pipeline, 5. Cloud Infrastructure & Production Hosting (Amazon Lightsail), 6. CORS Exception Handling Architecture, 7. Lifespan & Resilience Guarantees, 8. Observability & Langfuse Tracing, Compute Sizing & Memory Mechanics ("The Why") (+7 more)

### Community 196 - "format"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, filePatterns, format

### Community 197 - "lint"
Cohesion: 0.33
Nodes (6): cache, executor, options, outputs, lintFilePatterns, lint

### Community 199 - "Backend & FastAPI Standards"
Cohesion: 0.50
Nodes (3): Architecture & Framework (FastAPI), Backend & FastAPI Standards, Models / Schemas

### Community 201 - "Hermes Map (`libs/map`)"
Cohesion: 0.40
Nodes (4): 1. Commands, 2. Invariants, 3. Domain Triggers, Hermes Map (`libs/map`)

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

### Community 224 - "TypeScript & Frontend Standards"
Cohesion: 0.22
Nodes (8): 1. Agent Mandate & Core Principles, 2. Strict Type Safety & Prohibitions, 3. Type Modeling: Types, Interfaces & Enums, 4. Elegant & Concise Naming Conventions, 5. Monorepo Boundaries & Import Discipline, 6. React, State & Tactical GIS Architecture, 7. Formatting & Code Hygiene, TypeScript & Frontend Standards

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

### Community 306 - "EventTl"
Cohesion: 0.09
Nodes (17): 11.1 Commit matrix, 11.2 Session scopes in practice, 11.3 Composability limits, 11.5 PgBouncer-specific discipline, 11. Transactions, Sessions, and Concurrency, 14.1 Failure-mode matrix, 14.2 Startup sequence and what "ready" means, 14.3 Source sync failure semantics (+9 more)

### Community 324 - "16. Change Playbooks and Tunables"
Cohesion: 0.18
Nodes (10): 14.5 Observability hooks, 16.1 Adding a column, 16.2 Changing the embedding dimension or model, 16.4 Adding or changing a source, 16.6 Changing scoring or ranking weights, 16.7 Adding a service, 16.8 Migration workflow and safety, 16.9 Tunables reference (+2 more)

### Community 328 - "init_db"
Cohesion: 0.08
Nodes (10): _HtmlTextExtractor, 17.2 Module-level engine complicates multi-database use, 4.1 Pure Library Separation, 4.2 Engine and session factory, 4.3 Startup, request, and shutdown flow, 4.4 PgBouncer and prepared statements, 4. Configuration and Engine Lifecycle, 9.7 Source scheduling and catalog sync (+2 more)

### Community 329 - "SearchFilters"
Cohesion: 0.18
Nodes (6): 16.5 Adding a search filter, _age_hours_expr(), BoundingBox, _event_columns(), SearchFilters, SearchScope

## Knowledge Gaps
- **21 isolated node(s):** `../../tsconfig.base.json`, `../../tsconfig.base.json`, `../../../tsconfig.base.json`, `../../../../tsconfig.base.json`, `../../tsconfig.base.json` (+16 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1924 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **103 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `5. API Surface & Guards` connect `core/exceptions.py` to `DbChatRetriever`, `ChatRuntime`, `use-chat.ts`, `AiConfig`, `sse.ts`, `SearchService`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `EventService` (e.g. with `Architecture & Boundaries` and `get_event()`) actually correct?**
  _`EventService` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `../../tsconfig.base.json`, `../../tsconfig.base.json`, `../../../tsconfig.base.json` to the rest of the system?**
  _21 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sanitization.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06386066763425254 - nodes in this community are weakly interconnected._
- **Why does `ChatStreamEvent` connect `sse.ts` to `chat-store.ts`, `api-types.ts`, `core/exceptions.py`, `use-chat.ts`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 66 inferred relationships involving `run()` (e.g. with `.test_executes_exactly_one_query()` and `.test_returns_correct_bool()`) actually correct?**
  _`run()` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Should `GeocodingService` be split into smaller, more focused modules?**
  _Cohesion score 0.047339593114241005 - nodes in this community are weakly interconnected._