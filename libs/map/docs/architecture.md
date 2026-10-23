# Hermes Map — Architecture & Design Rationale

> [!NOTE]
> This is human-readable design documentation. It is not auto-loaded into agent context during standard sessions. Consult this document when modifying WebGL rendering layers, viewport debouncing, camera animation curves, or overlay positioning architecture.

---

## 1. Module Boundary & Portability

`@hermes/map` encapsulates the complete Mapbox GL JS WebGL rendering ecosystem, geospatial queries, and temporal graph visualization.

- **Decoupled Architecture**: Consumer shells (`apps/hermes`) supply environment credentials via `<MapConfigProvider config={{ baseUrl, apiVer, mapboxToken }}>` and mount `<MapView />`. The library never accesses `process.env` or `import.meta.env` directly, preserving portability across alternative host shells or testing environments.
- **Strict Boundary**: The map engine owns viewport telemetry, spatial projection, clustering, and timeline overlays. Surrounding UI shells (e.g. `LiveClock`, `BootSequence`) communicate solely via shared Zustand state or component composition.

---

## 2. Engineering Decisions, Constraints & Tradeoffs ("The Why")

### WebGL GPU Native Layers vs. DOM Markers
- **Decision**: All clustered nodes and unclustered event pins are rendered directly in the Mapbox WebGL canvas (`circle` and `symbol` layers) rather than HTML DOM markers (`new mapboxgl.Marker()`).
- **Why**: DOM markers create separate HTML nodes whose positions must be recalculated and reflowed by the browser layout engine on every frame during panning and zooming. Beyond a few hundred elements, layout thrashing degrades frame rates. WebGL instanced rendering processes thousands of points directly on the GPU with zero DOM churn.
- **Cluster Parameters**: Tuned to balance spatial legibility with tap target usability on high-DPI screens.

### Strict `useRef` Map Instance (Never `useState`)
- **Decision**: The `mapboxgl.Map` instance is stored exclusively in a `useRef<mapboxgl.Map | null>(null)`.
- **Why**: `mapboxgl.Map` is an enormous, deeply stateful object with internal render loops, event emitters, and WebGL contexts. Storing it in React `useState` causes React to perform shallow/deep comparison checks, resulting in infinite re-render spirals, garbage collection pressure, and dropped frames.

### Zustand (`useMapStore`) as Single Source of Truth
- **Decision**: Viewport bounding box (`north, south, east, west`), selected event coordinates, and timeline inspection modes are managed in a global Zustand store.
- **Why**: Mapbox event listeners fire from the WebGL thread outside React's synthetic event tree. Storing telemetry in Zustand provides instant, zero-boilerplate synchronization across React overlays (`EventPopup`, `TlPanel`), TanStack Query hooks, and root HUD components without prop drilling or split-brain race conditions.

### Viewport Telemetry & TanStack Query Debouncing
- **Decision**: Viewport bounding boxes update on `moveend` (rather than continuous `move` or `render`), clamped strictly within `[-90, 90]` latitude and `[-180, 180]` longitude, and queried via TanStack Query.
- **Why**: Firing spatial queries on every drag frame would flood `hermes-api` and PostGIS with unmanageable `ST_Within` requests. Updating on `moveend` naturally coalesces user interactions. Clamping coordinates prevents PostGIS `ST_MakeEnvelope` geometry exceptions when users pan past Mercator bounds (latitudes > 85°).

### Coordinate Screen Projection Pattern for Overlays
- **Decision**: Floating HUD overlays (`EventPopup`) compute screen positions using `requestAnimationFrame` + `map.project(lngLat)` rather than attaching to Mapbox DOM markers.
- **Why**: Decouples the React component tree from Mapbox DOM lifecycle. Enables viewport clamping (`Math.max` / `Math.min`) so modals never overflow outside the browser viewport, and allows pure CSS hardware-accelerated transforms (`translate3d`) synchronized to the monitor refresh rate.

### Camera Motion Physics & Smooth Interpolation
- **Decision**: Differential camera easing curves:
  - **Pin Selection**: `map.easeTo({ center, duration, easing: (t) => t * (2 - t) })` (Smooth quadratic ease-out).
  - **Cluster Expansion**: `map.easeTo({ center, zoom, duration, easing: (t) => t })` (Linear easing for snappy, tactical drill-down).
  - **Timeline Milestone Hops**: `map.flyTo({ center, zoom, duration })` (Parabolic curve maintaining geographical spatial context during historical hops).
- **Why**: Distinct motion physics convey intentional tactical feedback while preventing user disorientation across varying zoom scale changes.

### Timeline Drawer (`TlPanel`) Lifecycle & Dynamic Injection
- **Decision**: `TlPanel` dynamically injects `tl-nodes-source`, `tl-edges-source`, `tl-nodes-layer`, and `tl-edges-layer` on mount, tearing them down on unmount.
- **Why & Nuance**:
  - Employs a `mountId = useRef({})` dependency trigger in `useEffect` so that layer teardown and initialization execute reliably every time the panel opens, bypassing issues where a stable `map` ref suppresses re-execution.
  - Base layers (`hermes-clusters`, `hermes-unclustered-point`) are toggled via `getLayer()` check rather than `map.isStyleLoaded()`. `isStyleLoaded()` returns `false` during network tile streaming, which would falsely block visibility transitions.

### Client-Side Spatial Deduplication & Priority Ranking
- **Decision**: `createGeoJson` groups events by coordinate keys rounded to 4 decimal places (`toFixed(4)` ≈ 11m resolution).
- **Why**: Multiple RSS reports often share identical city-center geocodes. Deduplicating by selecting the maximum `trending_score` eliminates z-index fighting and visual stacking glitches, assigning dynamic rank-based radii to prominent stories.
