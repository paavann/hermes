# Hermes Map — AI Agent Context

## 1. Library Boundary
This library encapsulates the entire Mapbox GL JS ecosystem. The consumer app (`apps/hermes`) should only need to mount `<MapView />` and provide API configuration. 

## 2. Map Instance Lifecycle Rationale
The Mapbox `Map` instance is stored exclusively in a `useRef` (`const map = useRef<mapboxgl.Map | null>(null)`). **Never use `useState` for the map instance.** Storing complex WebGL contexts in React state triggers severe performance degradation and infinite re-render loops.

## 3. Coordinate Projection Pattern
React components that need to float above specific geographic coordinates (like `EventPopup`) do not use Mapbox DOM markers. Instead, they run a `requestAnimationFrame` loop calling `map.project(lngLat)` to calculate precise `(x, y)` screen pixels. This decouples the React UI lifecycle from the Mapbox rendering pipeline.

## 4. Timeline Layer Re-Injection
The `TlPanel` injects timeline edges and nodes dynamically into the map. It uses a `mountId = useRef({})` dependency array trick. This guarantees that whenever the panel mounts, it completely tears down and rebuilds its Mapbox layers, sidestepping issues where a stable `map` reference might swallow state changes.

## 5. GeoJSON Client-Side Deduplication
Because dense event clusters can overlap at the exact same coordinates, `createGeoJson` groups events by mathematically rounded coordinates (`toFixed(4)`). It promotes the event with the highest `trending_score` to rank 1, mapping it to a larger visual radius.
