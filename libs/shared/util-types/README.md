# `@hermes/util-types`

Shared TypeScript contracts for the Hermes REST API and chat SSE stream. The package is type-only; it ships no runtime transport or state logic.

## Contents

| Area | Types |
| :--- | :--- |
| Map and events | `MapEventResponse`, `EventResponse`, `EventDetailResponse`, `ArticleResponse` |
| Timelines | `TlResponse`, `TlNodeResponse`, `TlEdgeResponse` |
| Chat requests | `ChatRequest`, `ChatScope` (`event`, `viewport`, `global`), `ChatBoundingBox` |
| Chat stream | `ChatStreamEvent` discriminated union of `status`, `token`, `sources`, `done`, and `error` events |
| Chat metadata | `ChatSource`, `ChatProvenance`, `ChatCoverage`, `ChatUsage`, `ChatDegradedFlag`, `ChatErrorCode` |

The chat fixtures in [`fixtures/chat/`](fixtures/chat/) are shared examples for each request/event variant. `api-types.spec.ts` asserts that every fixture still matches the declared types and that the stream union narrows correctly.

## Contract Synchronization

These interfaces are hand-mirrored from the Pydantic response models in `apps/hermes-api/src/hermes_api/schemas/events.py` (and the chat models it references). When a Pydantic response schema changes, update `libs/shared/util-types/src/lib/api-types.ts` in the same task. There is no code generation step.

## Commands

```bash
npx nx lint @hermes/util-types
npx nx typecheck @hermes/util-types
npx nx test @hermes/util-types
```

## Related Docs

- [`apps/hermes-api/README.md`](../../../apps/hermes-api/README.md) — endpoint contracts and streaming behavior.
- [`docs/architecture.md`](../../../docs/architecture.md) — end-to-end request and chat flows.
