# `@hermes/map`

Mapbox GL JS map engine for Hermes: GPU-rendered event layers, viewport telemetry, event detail popups, citation highlights, and the historical timeline drawer.

The library is a browser-only rendering layer. It fetches from the REST API through TanStack Query and keeps shared map state in a Zustand store; it does not own server data or routing.

## Entry Points

| Export | Purpose |
| :--- | :--- |
| `MapView` | Full-bleed Mapbox canvas with cluster, point, citation, and timeline layers. |
| `useMapStore` | Zustand store for viewport, selection, timeline mode, citations, and focus requests. |
| `MapConfigProvider`, `useMapConfig` | Injected `baseUrl`, `apiVer`, and `mapboxToken`; no direct env access. |

## State And Data Flow

`useMapStore` is the single source of truth for:

- `viewport` — bounding box updated on `moveend`.
- `selectedEventId` / `selectedEventLngLat` — popup selection.
- `isTlMode` / `tlTargetId` — timeline drawer mode.
- `citedEvents` — chat citation rings rendered by a dedicated GeoJSON source.
- `focusRequest` — nonce-bearing camera request that flies to a cited event.

Hooks fetch only from the injected API config:

- `useMapDataSync` queries `/api/{apiVer}/events/bbox` for the current viewport (5 s stale time).
- `useEventDetails` queries `/api/{apiVer}/events/{id}` (60 s stale time).
- `useTl` calls `POST /api/{apiVer}/events/tl/{id}`, polls every 3 s while `GENERATING`, and exposes `regenerate` with `force_refresh=true`.

`MapView` requires a TanStack Query client and a `MapConfigProvider` ancestor. Because Mapbox needs browser globals, the SSR client must mount it behind a lazy boundary.

## Rendering Model

- Events arrive as a clustered GeoJSON source: two cluster layers (`hermes-clusters`, `hermes-cluster-count`) and one unclustered pin layer (`hermes-unclustered-point`).
- Events are sorted by descending `importance_score` before insertion; Mapbox clustering resolves visual collisions without hiding co-located pins.
- Citations render from `cited-events-source` as unclustered highlight rings.
- `TlPanel` injects and removes its own node/edge sources and layers on mount/unmount.
- `EventPopup` is projected with `map.project()` and positioned with CSS transforms; no `mapboxgl.Marker` DOM nodes are used.
- The Mapbox instance lives in `useRef`, never `useState`, and is treated as a pure rendering sink.

## Commands

Run from the workspace root:

```bash
npx nx lint @hermes/map
npx nx typecheck @hermes/map
npx nx test @hermes/map
```

## Related Docs

- [`AGENTS.md`](AGENTS.md) — invariants and domain triggers.
- [`.agents/rules/standards.md`](.agents/rules/standards.md) — WebGL layer, projection, and camera conventions.
- [`docs/architecture.md`](../../docs/architecture.md) — spatial synchronization and system context.
