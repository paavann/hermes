# Hermes Frontend Architecture & Rationale

This document contains human-readable architectural context, tradeoffs, and design rationale for `apps/hermes`. It is not auto-loaded into agent context; read this document when modifying authentication, route loaders, SSR configurations, or routing boundaries.

## 1. Application Role & Architecture Boundary

`apps/hermes` functions as a routing and provider composition shell. Under monorepo boundaries:
- **Application Scope**: Manages top-level routes (`app/routes.tsx`), root HTML layout and middleware (`app/root.tsx`), route-level data loaders, environment variable bindings, and application toolchain configuration.
- **Library Scope**: Domain business logic, geospatial rendering, state stores, spatial queries, and reusable UI components are isolated within dedicated libraries (`libs/map`, `libs/chat`, `libs/shared/ui-components`, `libs/shared/util-types`).

### Tradeoffs
Isolating routing and configuration within the application shell prevents framework-level coupling across domain libraries. It preserves portability for UI components and spatial stores across alternative execution environments (such as testing harnesses or embedded views) while enforcing unidirectional dependency boundaries.

## 2. Server-Side Rendering (`ssr: true`) & Authentication Guarding

The application operates in Server-Side Rendering (SSR) mode via `react-router.config.ts`.

### Authentication Guarding
Authentication middleware (`clerkMiddleware`) and session loading (`rootAuthLoader`) execute during server rendering in `app/root.tsx`. Route loaders inspect user credentials via `getAuth` before serving protected pages:
- `/map` checks `userId` server-side and redirects unauthenticated requests to `/auth`.
- `/auth/*` redirects authenticated users with active sessions to `/map`.
- Architectural intent: Evaluating credentials during server request handling prevents unauthenticated content flashing before client hydration (believed, not measured).

### Hydration Mechanics
The server-rendered document delivers the document shell, metadata tags, and tactical fallback structures. Interactive clients hydrate on mount, establishing client-side event listeners and initiating data querying.

## 3. WebGL Canvas Isolation & SSR Boundary Analysis

Mapbox GL requires active browser window and canvas contexts (`window`, `document`, and WebGL interfaces) that do not exist in Node.js server runtimes.

### Realized Mechanism & Limitations
In `apps/hermes/app/routes/map.tsx`, the map and chat containers are wrapped inside a single dynamic component boundary:
- `DynamicMapContainer` wraps parallel dynamic imports of `@hermes/map` and `@hermes/chat` using `React.lazy`.
- A `<Suspense fallback={<MapLoadingFallback />}>` boundary encloses the dynamic component.
- The underlying `@hermes/map` entrypoint (`libs/map/src/lib/ui/map-view.tsx`) imports `mapbox-gl` directly at module scope.
- The lazy factory itself only defines the composed component; no browser API runs until the client renders it.

### Guarantees & Known Risk
- **What this mechanism does**: Separates the map and chat libraries into asynchronous code chunks, preventing synchronous bundling into the primary server entry chunk.
- **What this mechanism does not guarantee**: In React SSR streaming and component tree evaluation, `React.lazy` without an explicit client-only execution gate (e.g., an `isMounted` state guard, `<ClientOnly>` component, or `.client` route module) can be invoked during server render passes.
- **Known Risk**: Flagged for architectural review. If React SSR triggers evaluation of the lazy chunks on the server, the top-level `import mapboxgl from 'mapbox-gl'` in `libs/map/src/lib/ui/map-view.tsx` may attempt to access browser globals and fail in Node.js.
- **SSR Smoke Coverage**: `apps/hermes/tests/routes/map-ssr.spec.tsx` imports the route module and renders `HydrateFallback`/`MapLoadingFallback` in a Node environment to confirm that module load does not evaluate the map or chat chunks.

## 4. Map Rendering & Interaction Boundaries

- **GPU Canvas Rendering vs. DOM Markers**: Map pins and clustered event counts are rendered directly through WebGL circle and symbol layers on the GPU canvas. Avoid creating off-screen or per-pin DOM elements; mounting extensive collections of DOM nodes is believed (not measured) to degrade frame rates and cause DOM bloat.
- **Accessible Overlays**: Because WebGL canvas contents are opaque to screen readers, accessible interaction occurs through HTML overlay panels (`EventPopup`, `TlPanel`, and HUD widgets). These overlays must maintain semantic markup, keyboard accessibility, and ARIA roles.

## 5. Design System Integration

The user interface implements a high-density tactical display:
- **Zero Border Radius**: Border radius utility tokens are reset (`--radius-*: initial;`) in `apps/hermes/styles.css`. Components must not apply `rounded-*` classes.
- **Design Tokens**: Colors, typography, and HUD borders are defined via theme variables in `apps/hermes/styles.css`. Hardcoded color literals and font family definitions must be avoided in component templates.

## 6. Provider Composition & Data Boundaries

The document shell and root layouts structure providers in a strict hierarchy:
1. **Document Shell (`app/root.tsx`)**: Initializes `ClerkProvider` for authentication context and configures document-level HTML, metadata, and Tailwind CSS.
2. **Route Boundaries (`app/routes/map.tsx`)**: Instantiates `QueryClientProvider` (TanStack Query) for server and client state caching.
3. **Map Configuration Provider (`MapConfigProvider`)**: Injects runtime API configuration (`baseUrl`, `apiVer`, `mapboxToken`) down to `@hermes/map` without coupling library code to Vite or environment globals.
4. **Chat Configuration Provider (`ChatConfigProvider`)**: Injects `baseUrl` and `apiVer` down to `@hermes/chat` so the library never reads `import.meta.env`.

The lazy composition tree in `apps/hermes/app/routes/map.tsx` is:

```text
Suspense (MapLoadingFallback)
└── DynamicMapContainer (React.lazy)
    └── MapConfigProvider
        └── ChatConfigProvider
            ├── MapView
            └── div[hidden = isTlMode]
                └── ChatPanel
```

## 7. Conversational RAG UI & Map Integration

### Composition
`ChatPanel` is an overlay, not a route. It owns its `useChat` hook and renders a closed-state tab when `isOpen` is false. The map remains full-bleed, visible, and interactive; closing the panel only flips `isOpen`, so the module-level Zustand store preserves the conversation and map viewport across close/reopen. The panel is hidden (not unmounted) while timeline inspection mode is active, so an in-flight stream and the conversation survive a mode switch without competing with `TlPanel`.

### Scope Resolution
The panel receives `autoScope` from the map store (`selectedEventId` and `viewport`) and resolves each request:

| Mode       | Resolution                                                     |
| :--------- | :------------------------------------------------------------- |
| `auto`     | selected event, else viewport, else global                     |
| `event`    | selected event, else viewport, else global                     |
| `viewport` | current viewport, else global                                  |
| `global`   | global plottings                                               |

The explicit mode persists in the chat store, while the underlying event ID and bounding box keep following the map.

### Citation Focus
`ChatPanel.onCitationActivate` is wired to `useMapStore.focusEvent` for event, article, and timeline sources that have an `event_id` and coordinates. `focusEvent` records a monotonically increasing `FocusRequest.nonce`, sets `selectedEventId`/`selectedEventLngLat` (opening `EventPopup`), and `MapView` flies to the coordinates at a minimum zoom of 6 on every nonce. Web citations are opened in a new tab by `useChat` and never move the map; sources without coordinates render as inert text.

### Highlight Lifecycle
The `sources` event is converted by `citedEventsFromSources` into deduplicated plotted events and written to `useMapStore.citedEvents`. `MapView` keeps a separate unclustered GeoJSON source (`cited-events-source`) and ring layer (`hermes-cited-points`) above the pins, so cited events outside the viewport remain highlighted after the camera arrives. The ring layer is hidden in timeline mode. Closing or clearing the conversation invokes `onSources([])`, which empties `citedEvents` and removes every highlight.

## 8. Production Hosting & Network Topology

- **Vercel Node.js SSR**: Deployed at `hermes-eight-inky.vercel.app`. Route loaders evaluate auth cookies and render initial document HTML on edge/server instances.
- **Direct API Ingress**: Client-side queries issued via TanStack Query communicate directly with `hermes-api` hosted on Render without intermediate proxy layers. CORS headers returned by the API ensure secure cross-origin communication.

