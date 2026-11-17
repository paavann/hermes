# Hermes Web Client (`@hermes/hermes`)

[![React 19](https://img.shields.io/badge/React-19.2-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![React Router 8](https://img.shields.io/badge/React_Router-8.3-CA4245?style=flat&logo=react-router&logoColor=white)](https://reactrouter.com)
[![Tailwind CSS 4](https://img.shields.io/badge/Tailwind-4.3-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Mapbox GL JS](https://img.shields.io/badge/Mapbox_GL-v3.29-4264FB?style=flat&logo=mapbox&logoColor=white)](https://docs.mapbox.com/mapbox-gl-js/)
[![Clerk Auth](https://img.shields.io/badge/Auth-Clerk-6C47FF?style=flat&logo=clerk&logoColor=white)](https://clerk.com)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)

The `@hermes/hermes` application is the React 19 frontend shell for the Hermes geospatial intelligence platform, deployed in production on Vercel at [hermes-eight-inky.vercel.app](https://hermes-eight-inky.vercel.app). It provides the user interface for monitoring global events through an interactive WebGL map, asking grounded questions about the current map scope, managing user authentication, and exploring historical event lineages.

---

## Architecture & Responsibilities

In accordance with workspace architectural invariants, `apps/hermes` operates as an **ultra-thin routing and provider composition shell**:

- **Shell Scope (<20%)**: Manages top-level routes ([`app/routes.tsx`](app/routes.tsx)), root document layout and middleware ([`app/root.tsx`](app/root.tsx)), server-side route loaders, environment variable injection, and toolchain configurations.
- **Library Scope (>80%)**: All heavy domain logic, WebGL canvas lifecycle management, Mapbox layer rendering, Zustand telemetry stores, conversational chat UI, and tactical UI primitives are isolated within workspace libraries ([`libs/map`](../../libs/map), [`libs/chat`](../../libs/chat), [`libs/shared/ui-components`](../../libs/shared/ui-components), and [`libs/shared/util-types`](../../libs/shared/util-types)).

> [!NOTE]
> For a deep dive into the server rendering mechanics, dynamic WebGL isolation, and design decisions, see [apps/hermes/docs/architecture.md](docs/architecture.md).

---

## Route Structure

Routes are declared in [`app/routes.tsx`](app/routes.tsx) using the React Router 8 file and route configuration:

| Route Path | Module | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `/` | [`app/routes/landing.tsx`](app/routes/landing.tsx) | Public | Operational landing page introducing platform capabilities, problem statement, and launch entry points. |
| `/map` | [`app/routes/map.tsx`](app/routes/map.tsx) | Protected | The primary tactical map interface. Hosts the WebGL Mapbox canvas, event clusters, detail popups, and the timeline lineage drawer. |
| `/auth/*` | [`app/routes/auth.tsx`](app/routes/auth.tsx) | Public / Flow | Multi-step authentication workflow (Email, OTP, Password, Setup, and SSO callbacks) powered by Clerk. |
| `/privacy` | [`app/routes/privacy.tsx`](app/routes/privacy.tsx) | Public | Privacy policy and data-handling disclosures. |
| `__clerk/*` | [`app/routes/clerk-proxy.ts`](app/routes/clerk-proxy.ts) | Proxy | Clerk proxy handler for same-origin authentication requests. |

---

## Server-Side Rendering (SSR) & WebGL Isolation

The application is configured with `ssr: true` in [`react-router.config.ts`](react-router.config.ts), executing within a Node.js server environment in production.

### 1. Server-Side Access Control
Authentication is verified server-side inside route loaders using Clerk's `getAuth` before rendering the document shell:
- Requests to `/map` without an active session are redirected server-side to `/auth`, eliminating unauthenticated UI flashes.
- Authenticated requests visiting `/auth` are automatically redirected to `/map`.

### 2. Client-Only WebGL & Chat Dynamic Boundary
Mapbox GL JS requires browser globals (`window`, `document`, and WebGL contexts) that do not exist during Node.js server execution. To maintain SSR compatibility without hydration failures:
- `DynamicMapContainer` wraps parallel dynamic imports of [`MapView`](../../libs/map/src/lib/ui/map-view.tsx) and `ChatPanel` from `@hermes/chat` within [`app/routes/map.tsx`](app/routes/map.tsx).
- A `<Suspense fallback={<MapLoadingFallback />}>` boundary renders a lightweight animated placeholder while the client hydrates and loads the map and chat bundles.

---

## Data Synchronization & State Architecture

```mermaid
flowchart LR
    subgraph ClientUI ["React 19 Frontend (apps/hermes)"]
        MapView["MapView (WebGL Canvas)"]
        Zustand["useMapStore (Zustand)\nViewport Bounding Box"]
        ReactQuery["useMapDataSync (TanStack Query)\nDebounced BBox Query"]
    end

    subgraph BackendAPI ["FastAPI REST Service (hermes-api)"]
        BboxEndpoint["GET /api/v1/events/bbox\n(Spatial PostGIS Query)"]
    end

    MapView -->|"Pan / Zoom (onMoveEnd)"| Zustand
    Zustand -->|"Updates viewport bounds"| ReactQuery
    ReactQuery -->|"HTTP GET"| BboxEndpoint
    BboxEndpoint -->|"MapEventResponse[]"| ReactQuery
    ReactQuery -->|"setData()"| MapView
```

- **Single Source of Truth**: Viewport coordinates (`north`, `south`, `east`, `west`), event selection (`selectedEventId`), timeline mode (`isTlMode`), and chat citation highlights (`citedEvents`) reside in [`useMapStore`](../../libs/map/src/lib/store/store.ts).
- **Decoupled Configuration**: Credentials and API base URLs are provided declaratively to domain hooks via [`MapConfigProvider`](../../libs/map/src/lib/config-context.tsx) and [`ChatConfigProvider`](../../libs/chat), preventing libraries from directly referencing `import.meta.env`.
- **Conversational RAG**: [`ChatPanel`](../../libs/chat) is an overlay over the map, not a route. It resolves `auto` scope from the selected event/viewport, streams answers from `POST /api/v1/chat`, renders citations, and forwards cited event coordinates to `useMapStore.focusEvent`.

---

## Tactical Design System

The application enforces a high-density, mission-control visual theme:

- **Zero Border Radius**: Border radius utility tokens are globally reset (`--radius-*: initial;`) in [`styles.css`](styles.css). Components strictly avoid `rounded-*` utility classes.
- **Monospace Typography**: `JetBrains Mono` is the display and UI face, with `Fira Code` as the fallback stack.
- **Tactical Palette**: Pure black canvas (`#000000`) with solid obsidian (`#07080A`), onyx (`#0B0D10`), and graphite (`#12151A`) surfaces, cyan primary accent (`#00F0FF`), warm bone/ivory text (`#D7D0BF` / `#F1EDE2`), and amber signal accents (`#FFB454`).
- **Strictly Solid Surfaces**: Panels use opaque fills and `1px` hairline borders; glassmorphism, backdrop blur, and glow shadows are prohibited.
- **Shared UI Primitives**: shadcn-style primitives (buttons, inputs) are maintained in [`libs/shared/ui-components`](../../libs/shared/ui-components), never created ad-hoc in `apps/hermes`.

---

## Environment Configuration

The application consumes environment variables configured in the repository root `.env` or set in the deployment dashboard:

| Variable | Required | Description |
| :--- | :--- | :--- |
| `VITE_MAPBOX_TOKEN` | Yes | Mapbox public access token for WebGL tiles and map rendering. |
| `VITE_BASE_URL` | Yes | HTTP base URL of the backend REST service (e.g. `http://localhost:8000`). |
| `VITE_API_VER` | Yes | REST API version prefix (default: `v1`). |
| `VITE_CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key used for client authentication workflows. |
| `CLERK_SECRET_KEY` | Yes | Clerk secret key used by server loaders during SSR request evaluation. |
| `VITE_CLERK_PROXY_URL` | Prod | Clerk proxy URL routed through the `__clerk/*` handler; used by `ClerkProvider` in production. |

---

## Development Commands

All commands are executed from the monorepo root:

```bash
# Start the local development server (Vite on port 4200)
npx nx dev hermes

# Build the production application bundle
npx nx build @hermes/hermes

# Run unit and component test suites (Vitest)
npx nx test @hermes/hermes

# Run ESLint validation
npx nx lint @hermes/hermes

# Run TypeScript type verification
npx nx typecheck @hermes/hermes
```
