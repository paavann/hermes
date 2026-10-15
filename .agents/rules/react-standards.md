---
trigger: glob
description: Strict React 19 standards, React Router v8 architecture, directory conventions, shadcn and Tailwind v4 integration, hooks hygiene, and state architecture.
globs: '**/*.tsx, **/use-*.ts, **/use*.ts, **/react-router.config.ts, **/routes.tsx'
---

# React & React Router Standards

Official engineering guidelines, architectural paradigms, and coding conventions for all React (`.tsx`) and React Router code in Hermes (`apps/hermes`, `libs/map`, `libs/shared/ui-components`).

---

## 1. Official Documentation Mandate

All agents MUST strictly consult and adhere to official documentation for best practices:
- **React 19 Core & Best Practices**: [https://react.dev/learn](https://react.dev/learn) (pure components, escape hatches, concurrent features).
- **React Router v8 Architecture**: [https://reactrouter.com/home](https://reactrouter.com/home) (framework mode, typed route modules, navigation, data loading).

---

## 2. Directory Structure & The 80/20 Shell Doctrine

Applications (`apps/hermes`) follow official React Router v8 conventions in SPA mode (`ssr: false`):

```text
apps/hermes/
├── app/
│   ├── root.tsx            # Document shell (<html>, <head>, <Meta />, <Links />, <Outlet />, <Scripts />)
│   ├── routes.tsx          # Central route manifest via @react-router/dev/routes (index, route, layout)
│   ├── routes/             # Thin route orchestration shells (<20%)
│   │   ├── landing.tsx
│   │   ├── map.tsx
│   │   └── about.tsx
│   ├── entry.client.tsx    # Client hydration entry
│   ├── entry.server.tsx    # Build-time shell entry
│   └── styles.css          # Global Tailwind v4 entry (@import 'tailwindcss'; @theme)
├── react-router.config.ts  # SPA configuration (ssr: false)
└── vite.config.mts         # Vite build toolchain
```

### The 80/20 Route Rule
- **Routes Are Thin Orchestration Shells (<20%)**: Route files in `app/routes/` only handle metadata (`meta`), asset links (`links`), loaders (`clientLoader`), route-level `ErrorBoundary`, and layout assembly from `libs/`.
- **Heavy Logic Strictly in `libs/` (>80%)**: Spatial queries, Mapbox layers, Zustand telemetry, and reusable UI MUST live in `libs/map` or `libs/shared/ui-components`. Never write monolithic logic in `app/routes/`.

```typescript
// apps/hermes/app/routes/map.tsx (Thin Route Shell)
import type { MetaFunction } from 'react-router';
import { MapView } from '@hermes/map';
import { LiveClock } from '@hermes/ui-components';

export const meta: MetaFunction = () => [{ title: 'Hermes — Live Map' }];

export default function MapRoute(): React.JSX.Element {
  return (
    <main className="relative w-full h-dvh overflow-hidden bg-black">
      <MapView />
      <LiveClock />
    </main>
  );
}
```

---

## 3. Monorepo UI Architecture & Strict shadcn Discipline

- **Centralized Primitives**: ALL primitive UI elements (buttons, dialogs, dropdowns, inputs, tooltips) MUST reside in [`libs/shared/ui-components/src/components/ui/`](file:///home/pavan/proj/hermes/libs/shared/ui-components/src/components/ui/).
- **Strict Prohibition of Local Primitives**: Apps (`apps/*`) and feature libs (`libs/map`) are strictly forbidden from creating local base primitives. Import from `@hermes/ui-components`.
- **shadcn Alignment**: Follow [`components.json`](file:///home/pavan/proj/hermes/libs/shared/ui-components/components.json) using `base-sera` style, `@base-ui/react` primitives, and `@phosphor-icons/react`.
- **Class Merging**: Always use `cn()` from `@hermes/ui-components` (`clsx` + `tailwind-merge`).
- **Composite HUD Widgets**: Reusable tactical widgets (`BootSequence`, `LiveClock`) live in `libs/shared/ui-components/src/lib/` and export through `src/index.ts`.

---

## 4. Tailwind CSS v4 & Tactical Styling Discipline

Hermes uses Tailwind CSS v4 with CSS-first configuration:
- **Utility-First**: Style strictly with Tailwind utility classes merged via `cn()`.
- **No Inline Styles**: Arbitrary inline `style={{ ... }}` is strictly forbidden.
  - *Exception*: Dynamic, runtime WebGL/canvas coordinates or transforms (e.g., `style={{ transform: \`translate3d(\${x}px, \${y}px, 0)\` }}`).
- **No Scattered CSS Files**: Standalone `.css` or `.module.css` files are banned across components. All global tokens reside in [`apps/hermes/styles.css`](file:///home/pavan/proj/hermes/apps/hermes/styles.css) under `@theme`.
- **Zero Border Radius Mandate**: Never use `rounded-*` classes (`--radius-*: initial;` enforced). Sharp, rectangular corners only.
- **Monospace Typography**: All telemetry widgets, coordinate streams, and HUD elements must use `font-mono`.

```typescript
// Good: Utility-first styling with cn()
import { cn } from '@hermes/ui-components';

interface BadgeProps {
  className?: string;
  variant?: 'active' | 'warning';
  children: React.ReactNode;
}

export function Badge({ className, variant = 'active', children }: BadgeProps): React.JSX.Element {
  return (
    <span
      className={cn(
        'px-2 py-0.5 text-xs font-mono uppercase tracking-wider border',
        variant === 'active' && 'border-neon-blue text-neon-blue bg-neon-blue/10',
        variant === 'warning' && 'border-warning-yellow text-warning-yellow bg-warning-yellow/10',
        className
      )}
    >
      {children}
    </span>
  );
}
```

---

## 5. Modern React 19 Paradigms

Hermes runs on React 19 (`^19.2.8`):

### Direct `ref` as a Prop (`forwardRef` Forbidden)
Pass `ref` directly as a component prop. `React.forwardRef` is deprecated and strictly forbidden:

```typescript
// Bad: Legacy forwardRef
export const TacticalInput = React.forwardRef<HTMLInputElement, Props>((props, ref) => <input ref={ref} {...props} />);

// Good: React 19 direct ref prop
interface TacticalInputProps extends React.ComponentProps<'input'> {
  ref?: React.Ref<HTMLInputElement>;
}
export function TacticalInput({ ref, className, ...props }: TacticalInputProps): React.JSX.Element {
  return <input ref={ref} className={cn('bg-black border border-hud-border font-mono text-sm px-2 py-1', className)} {...props} />;
}
```

### Async Transitions & Actions
- Use `useTransition` for async state transitions to prevent UI freezing.
- Use `useActionState` and `useOptimistic` for form mutations and optimistic feedback instead of manual `isLoading` flags and `try/catch/finally` state soup.

### The `use()` Hook
- Use React 19's `use(Context)` for reading contexts conditionally within render boundaries instead of `useContext`.

---

## 6. The "You Might Not Need an Effect" Doctrine

Per [React Learn: You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect), `useEffect` is strictly for synchronizing with external systems:

1. **NO Effects for Derived State**: Compute derived values inline during render.
   ```typescript
   // Bad: Redundant state + effect sync
   const [filtered, setFiltered] = useState([]);
   useEffect(() => { setFiltered(items.filter((i) => i.active)); }, [items]);

   // Good: Computed inline during render
   const filtered = items.filter((i) => i.active);
   ```
2. **NO Effects for User Events**: Interaction logic belongs in event handlers, not state-triggered effects.
3. **NO Effects for Resetting State on Prop Change**: Pass a unique `key` prop to the component instead of syncing props in an effect (`<EventCommentBox key={eventId} eventId={eventId} />`).
4. **External Sync Only**: `useEffect` is strictly reserved for Mapbox canvas initialization, external DOM listeners, and observers. **Mandatory Cleanup**: Always return a cleanup function to prevent memory leaks:
   ```typescript
   useEffect(() => {
     const handleKeyDown = (e: KeyboardEvent): void => { if (e.key === 'Escape') onClose(); };
     window.addEventListener('keydown', handleKeyDown);
     return () => window.removeEventListener('keydown', handleKeyDown);
   }, [onClose]);
   ```

---

## 7. The 6-Tier State Management Hierarchy

To eliminate duplicate, stale, or shadow state, every state element MUST belong to exactly one tier:

| Tier | Domain | Tool / Mechanism | Rule |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **URL State** | React Router (`useSearchParams`, `useParams`) | Source of truth for shareable view state (filters, `?event=123`). |
| **Tier 2** | **Server State** | TanStack Query v5 (`useQuery`, `useMutation`) | Remote API data, caching, polling. Never duplicate in `useState`. |
| **Tier 3** | **Global Telemetry** | Zustand ([`useMapStore`](file:///home/pavan/proj/hermes/libs/map/src/lib/store/store.ts)) | Real-time tactical state. Use atomic selectors (`useMapStore((s) => s.viewport)`). |
| **Tier 4** | **Local UI State** | React `useState` / `useReducer` | Transient, component-scoped UI toggles (dropdown open, input focus). |
| **Tier 5** | **Derived State** | Inline Render Calculation (`useMemo`) | Calculated in render. Memoize only if profiling proves expensive. |
| **Tier 6** | **Transient Values** | React `useRef` | Non-rendering values (Mapbox instance, timer IDs, animation refs). |

**Prohibition of Shadow State**: Never copy state from a higher tier into a lower tier (e.g. no initializing local `useState` from TanStack Query or Zustand).

---

## 8. Tactical GIS & Mapbox Architecture

- **The Mapbox Ref Rule**: NEVER store the Mapbox GL `Map` instance in React state (`useState`), which triggers recursive re-renders and degrades 60 FPS WebGL performance. ALWAYS hold the map instance in `useRef<mapboxgl.Map | null>(null)`.
- **Mapbox as Pure Rendering Sink**: Mapbox receives updates and dispatches events (`useMapStore.getState().setViewport(bbox)`), but never stores application state.
- **Accessible Overlays**: Overlay panels (`EventPopup`, `TlPanel`) must provide semantic HTML, keyboard dismissal (`Escape`), focus trapping, and ARIA attributes (`role="dialog"`, `aria-label`).

---

## 9. Component Hygiene & Render Purity

- **Pure Rendering**: Components must be pure functions of props and state. Never mutate external variables or call APIs in the render body.
- **Rules of Hooks**: Call hooks strictly at the top level of function components or custom hooks.
- **Explicit Props Interface**: Every component accepting props must define an explicit `interface <ComponentName>Props`.
- **Composition Over Prop Drilling**: Use `children` or slot props instead of bloated multi-purpose components.
- **Declarative Error Handling**: Wrap major route outlets and feature trees with React Router / React `ErrorBoundary` components.
