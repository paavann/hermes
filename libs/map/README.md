# `@hermes/map`

Mapbox GL JS map engine for Hermes: GPU-rendered event layers, cross-event relationship arcs and actor vectors, viewport telemetry, event detail popups, citation highlights, story thread drawer, and historical timeline viewer.

The library is a browser-only rendering layer. It fetches from the REST API through TanStack Query and keeps shared map state in a Zustand store; it does not own server data or routing.

## Entry Points

| Export | Purpose |
| :--- | :--- |
| `MapView` | Full-bleed Mapbox canvas with event cluster/pin, relationship/actor vector, citation, timeline, and story thread layers/drawers (`threadId`, `onThreadChange`, `popupInsets`). |
| `useMapStore` | Zustand store for viewport, selection, timeline mode, relationship layer toggle (`showRelationships`), citations, and focus requests. |
| `MapConfigProvider`, `useMapConfig` | Injected `baseUrl`, `apiVer`, and `mapboxToken`; no direct env access. |
| `CitedEvent` | Plotted chat-citation coordinate contract consumed by `citedEvents`. |

## State And Data Flow

`useMapStore` is the single source of truth for:

- `viewport` — bounding box updated on `moveend`.
- `selectedEventId` / `selectedEventLngLat` — popup selection.
- `isTlMode` / `tlTargetId` — timeline drawer mode.
- `citedEvents` — chat citation rings rendered by a dedicated GeoJSON source.
- `focusRequest` — nonce-bearing camera request that flies to a cited event.
- `showRelationships` / `toggleRelationships` — visibility toggle for relationship arcs and actor vectors.

Hooks fetch only from the injected API config:

- `useMapDataSync` queries `/api/{apiVer}/events/bbox` for the current viewport (5 s stale time).
- `useMapRelationships` queries `/api/{apiVer}/events/relationships` for active viewport relationship edges (10 s stale time).
- `useEventDetails` queries `/api/{apiVer}/events/{id}` for full summary, articles, extracted actors, and connected relationships (60 s stale time).
- `useThreadDetails` queries `/api/{apiVer}/threads/{threadId}` for narrative thread details and ordered member events (60 s stale time).
- `useTl` calls `POST /api/{apiVer}/events/tl/{id}`, polls every 3 s while `GENERATING`, and exposes `regenerate` with `force_refresh=true`.

`MapView` requires a TanStack Query client and a `MapConfigProvider` ancestor. Because Mapbox needs browser globals, the SSR client must mount it behind a lazy boundary.

## Rendering Model

- **Events & Clustering**: Events render from `events-source` via two cluster layers (`hermes-clusters`, `hermes-cluster-count`) and one unclustered pin layer (`hermes-unclustered-point`, accented with a cyan stroke when `relationship_count > 0`). Clicking a cluster opens `ClusterList` when pins coincide or zooms in smoothly; clicking a pin opens `EventPopup`.
- **Relationships & Actor Vectors**: `relationship-geojson.ts` builds great-circle arcs (with antimeridian splitting) and actor vector lines/anchors styled by `relationship-theme.ts` (`CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`, dashed actor vectors), fed into `relationship-edges-source` (`hermes-relationship-arcs-glow`, `hermes-relationship-arcs`), `relationship-partners-source` (`hermes-relationship-partners`), `actor-vectors-source` (`hermes-actor-vectors`), and `actor-anchors-source` (`hermes-actor-anchors`). Toggleable from the `MapHud` connections control and automatically hidden in timeline mode.
- **Citations & Timelines**: Chat citations render from `cited-events-source` (`hermes-cited-points`). `TlPanel` injects and removes `tl-edges-layer` / `tl-nodes-layer` on mount/unmount.
- **Overlays**: `EventPopup` projects pin coordinates with `map.project()` via `requestAnimationFrame` (`PopupInsets` keeps clear of chat and story panels) and shows actors, connected events, thread links (`onThreadOpen`), and timeline launch. `StoryPanel` renders thread progression synchronized via URL `?thread=<id>`, `EventsLoader` signals background fetches, and `MapHud` provides the top/bottom tactical telemetry bars.
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
