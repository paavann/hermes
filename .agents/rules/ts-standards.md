---
trigger: glob
description: Strict TypeScript standards, compile-time type safety, concise naming conventions, and React patterns.
globs: '**/*.ts, **/*.tsx'
---

# TypeScript Standards

## Type Safety

- **No `any` or Loose `as` Casts**: `any` is forbidden—use `unknown` with user-defined type guards (`val is T`), Zod parsing, or constrained generics. Prefer `satisfies` over `as` assertions; use `as` only when third-party ambient types are demonstrably wrong.
- **Explicit Return Types**: Always declare explicit return types on exported functions, hooks, service methods, and utilities.
- **`interface` vs `type` & No Native `enum`**: Use `interface` for object contracts, props, and store states; use `type` for unions, intersections, and function signatures. Native TypeScript `enum` is forbidden—use string literal unions or `as const` objects.

## Naming & Monorepo Imports

- **Concise Identifiers**: Prefer clean, standard abbreviations (`pos`, `bbox`, `tl`, `cfg`, `ctx`, `el`, `err`, `fmt`, `lngLat`, `btn`) over bloated names, while avoiding single-letter mystery variables outside loop indices (`i`) and coordinates (`x, y`).
- **File & Symbol Casing**: Components in `PascalCase.tsx`; hooks (`use-*.ts`), stores, and utilities in `kebab-case.ts`; route shells in `kebab-case.tsx`. Internal event handlers prefix `handle*`, callback props prefix `on*`, constants in `UPPER_SNAKE_CASE`.
- **Import Discipline**: Always use `import type { ... }` for type-only imports. Cross-library imports must use `@hermes/*` path aliases (never relative `../../libs/...`). Group imports separated by blank lines: (1) external packages, (2) `@hermes/*` workspace libs, (3) relative local files, (4) `import type`.
