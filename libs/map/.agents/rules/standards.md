# Mapbox & GIS Standards (`libs/map`)

Coding standards, layer authoring conventions, and WebGL lifecycle patterns for `@hermes/map`.

---

## 1. WebGL Layer Authoring & Expressions

- **Data-Driven Styling**: Style circle radius, colors, and opacity using Mapbox GL expressions (e.g., `['step', ['get', 'point_count'], ...]`) bound to GeoJSON feature properties. Never run imperative JavaScript loops across feature arrays to adjust styles.
- **Layer Architecture**: Clustered event sources feed two distinct layers:
  - `hermes-clusters`: WebGL circle and symbol count layer for aggregate clusters.
  - `hermes-unclustered-point`: WebGL circle and label layer for individual incidents.
- **Dynamic Layer Teardown**: Dynamic inspection overlays (`TlPanel`) must inject sources and layers on mount and cleanly remove them on unmount (`map.removeLayer`, `map.removeSource`). Check `map.getLayer(layerId)` before removing or toggling visibility; never rely on `map.isStyleLoaded()`, which returns `false` during network tile streaming and falsely blocks transitions.
- **Re-mount Trigger Pattern**: When an overlay component depends on dynamic layer lifecycle across re-opens while retaining a stable `map` ref, track panel activations using a mutable `mountId = useRef({})` dependency inside `useEffect`.

---

## 2. Coordinate Screen Projection for Overlays

- **Screen Projection Over Markers**: Position floating HUD elements (`EventPopup`) via CSS transforms (`translate3d`) computed from `map.project(lngLat)` inside `requestAnimationFrame`. Do not bind React component portals to Mapbox DOM markers.
- **Viewport Clamping**: Constrain projected pixel coordinates with `Math.max` / `Math.min` boundaries against window dimensions to prevent HUD panels from overflowing viewport edges.

---

## 3. Viewport Debouncing & Bounds Clamping

- **Interaction Coalescence**: Dispatch viewport changes into `useMapStore` strictly on `moveend`, never on continuous `move` or `render` events.
- **Mercator Bounds Clamping**: Clamp latitude strictly to `[-90, 90]` and longitude to `[-180, 180]` before constructing bounding-box query parameters, preventing PostGIS `ST_MakeEnvelope` polygon errors on extreme pans.

---

## 4. Camera Motion Physics

Apply differential easing curves based on user intent:
- **Pin Selection**: Use `map.easeTo({ center, duration, easing })` with quadratic ease-out (`(t) => t * (2 - t)`) for smooth tactical centering.
- **Cluster Expansion**: Use `map.easeTo({ center, zoom, duration, easing: (t) => t })` with linear easing for rapid drill-down.
- **Timeline Milestone Hops**: Use `map.flyTo({ center, zoom, duration })` for parabolic camera arcs that preserve geographical context across large distances.

---

## 5. Spatial Deduplication Conventions

- **Coordinate Rounding**: In `createGeoJson`, group co-located events by coordinate keys rounded to 4 decimal places (`toFixed(4)` ≈ 11m resolution).
- **Ranking Resolution**: When co-located events collide, prioritize the event with the highest `trending_score` to avoid z-index fighting on the WebGL canvas.
