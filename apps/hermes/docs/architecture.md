# Hermes Frontend Architecture & Rationale

This document contains human-readable architectural context, tradeoffs, and design rationale for `apps/hermes`. It is not auto-loaded into agent context; read this document when modifying authentication, route loaders, SSR configurations, or routing boundaries.

## 1. Application Role & Architecture Boundary

`apps/hermes` functions as a routing and provider composition shell. Under monorepo boundaries:
- **Application Scope**: Manages top-level routes (`app/routes.tsx`), root HTML layout and middleware (`app/root.tsx`), route-level data loaders, environment variable bindings, and application toolchain configuration.
- **Library Scope**: Domain business logic, geospatial rendering, state stores, spatial queries, and reusable UI components are isolated within dedicated libraries (`libs/map`, `libs/shared/ui-components`, `libs/shared/util-types`).

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
In `apps/hermes/app/routes/map.tsx`, the map container is wrapped inside a dynamic component boundary:
- `DynamicMapContainer` wraps a dynamic import of `@hermes/map` using `React.lazy`.
- A `<Suspense fallback={<MapLoadingFallback />}>` boundary encloses the dynamic component.
- The underlying `@hermes/map` entrypoint (`libs/map/src/lib/ui/map-view.tsx`) imports `mapbox-gl` directly at module scope.

### Guarantees & Known Risk
- **What this mechanism does**: Separates the map library into an asynchronous code chunk, preventing synchronous bundling into the primary server entry chunk.
- **What this mechanism does not guarantee**: In React SSR streaming and component tree evaluation, `React.lazy` without an explicit client-only execution gate (e.g., an `isMounted` state guard, `<ClientOnly>` component, or `.client` route module) can be invoked during server render passes.
- **Known Risk**: Flagged for architectural review. If React SSR triggers evaluation of the lazy chunk on the server, the top-level `import mapboxgl from 'mapbox-gl'` in `libs/map/src/lib/ui/map-view.tsx` may attempt to access browser globals and fail in Node.js.

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

## 7. Production Hosting & Network Topology

- **Vercel Node.js SSR**: Deployed at `hermes-eight-inky.vercel.app`. Route loaders evaluate auth cookies and render initial document HTML on edge/server instances.
- **Direct API Ingress**: Client-side queries issued via TanStack Query communicate directly with `hermes-api` hosted on Render without intermediate proxy layers. CORS headers returned by the API ensure secure cross-origin communication.

