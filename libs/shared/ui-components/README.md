# `@hermes/ui-components`

Shared HUD component library for the Hermes client. It contains shadcn-style primitives plus the tactical chrome used across the landing page, auth screens, and map interface.

Styling is Tailwind CSS v4 with the workspace's cyan/bone/amber tokens. Components use sharp corners, solid surfaces, `font-mono` UI labels, and Phosphor icons. Design rules live in [`.agents/rules/ui-standards.md`](../../../.agents/rules/ui-standards.md).

## Components

| Export | Purpose |
| :--- | :--- |
| `Button`, `Input`, `Textarea`, `Label`, `Separator` | shadcn-style primitives (`base-sera` style registry) built on `class-variance-authority` and `cn`. |
| `TacticalActionBtn` | High-contrast HUD action button with hard hover inversion. |
| `RollButton` | GSAP text-roll navigation action; supports `to` (React Router), `href`, or `onClick`. |
| `CornerReticle` | L-shaped framing brackets for HUD containers. |
| `HermesWordmark` | SVG brand wordmark. |
| `LiveClock` | Tabular UTC clock readout. |
| `BootSequence` | GSAP scramble intro that calls `onComplete` when finished. |
| `OAuthButtonGroup` | Google, Facebook, and X auth buttons with an active-provider state. |
| `cn` | Tailwind-aware class-name merge helper from the `cn` package. |

`RollButton` imports `react-router`; consumers already using React Router satisfy that peer requirement. Components do not read environment variables or own page-level state.

## Adding Primitives

Install new shadcn primitives into this library, not into `apps/hermes`:

```bash
npx shadcn@latest add <component> --cwd libs/shared/ui-components
```

New primitives are exported from `src/index.ts`, and new HUD components belong in `src/lib/`.

## Commands

Run from the workspace root:

```bash
npx nx lint @hermes/ui-components
npx nx typecheck @hermes/ui-components
npx nx test @hermes/ui-components
```

## Related Docs

- [`AGENTS.md`](../../../AGENTS.md) — workspace layout and UI primitive rules.
- [`.agents/rules/ui-standards.md`](../../../.agents/rules/ui-standards.md) — palette, typography, geometry, and motion standards.
- [`apps/hermes/styles.css`](../../../apps/hermes/styles.css) — Tailwind theme tokens consumed by these components.
