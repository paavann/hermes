---
trigger: always_on
---

# Frontend & React Standards

- **Dumb Components / Custom Hooks**: Extract complex business logic, map state calculations, and data fetching into custom React hooks (e.g., `useMapEvents()`). UI components (returning JSX) must remain purely presentational.
- **Tailwind Exclusivity**: Use Tailwind CSS utility classes exclusively. Creating custom `.css` or `.scss` files is strictly forbidden unless absolutely necessary for complex Mapbox GL overrides. Extract reusable styles into React components rather than using `@apply`.
- **Zustand State**: NEVER mutate Zustand state directly. Strictly define and call action functions inside the store.
- **React Router Data**: Prioritize using React Router v7/v8 `loader` and `action` functions for route-level data fetching rather than triggering fetches inside `useEffect`.
- **File Naming & Casing**: Strictly use `camelCase.tsx` for all React files (e.g., `eventMarker.tsx`) and for naming variables, functions, and filenames in the JS/TS ecosystem.
- **Props**: ALWAYS destructure React props in the function signature (e.g., `function Map({ data }):`) rather than accessing them via `props.data`.
- **Exhaustive Deps**: Strictly follow React's `exhaustive-deps` rule. NEVER suppress the eslint warning (`// eslint-disable-next-line`) to make a bug go away.
- **TypeScript Strictness**:
  - NEVER use the `any` type. If unknown, use `unknown` and type-guard it.
  - Strictly use `interface` instead of `type` for object definitions (unless defining unions/intersections).
  - Use absolute path aliases (e.g., `import { Button } from '@hermes/ui'`) and avoid deep relative paths.
- **Testing**: Explicitly write Playwright E2E tests for the most critical user journeys.

## TanStack Query Best Practices

1. **Setup and Initialization**
   - **Global Provider:** Always wrap your application in a `QueryClientProvider` at the root (e.g., `app.tsx`).
   - **Client Instantiation:** Initialize new `QueryClient()` outside of your React component lifecycle to ensure a single, persistent instance.
2. **Querying Standards**
   - **Unique Query Keys:** Every `useQuery` call must have a unique `queryKey` as an array. If the query depends on variables (like an ID), include those variables in the key to ensure proper caching and invalidation.
   - **Pass Definitions, Not Calls:** Always pass the query function definition to `queryFn`, do not call the function (e.g., use `queryFn: getTodos` instead of `queryFn: getTodos()`).
3. **State Management**
   - **Leverage Built-in States:** Use returned booleans like `isPending`, `isError`, and `isFetching` instead of manual `useState` hooks for loading and error handling.
   - **Use isPending:** Prefer `isPending` for initial loading states where there is no cached data.
4. **Architecture and Reusability**
   - **Modular Options:** Move complex query configurations into a separate directory (e.g., `/queryOptions`) and utilize the `queryOptions` utility from TanStack Query for better type safety and code reusability.
5. **Type Safety**
   - **Explicit Return Types:** Define clear interfaces for your API responses. Ensure your query functions return a typed `Promise` to avoid `any` types and provide full Intellisense support in your components.
6. **Advanced Patterns**
   - **Conditional Queries:** Use the `enabled` property within `useQuery` to trigger queries conditionally based on component state.
   - **Suspense Integration:** Use `useSuspenseQuery` in conjunction with React's `<Suspense>` component to streamline loading states and simplify component logic.
   - **Batching Queries:** For independent multiple requests, use `useQueries` or `useSuspenseQueries` to consolidate calls.
7. **Mutations and Updates**
   - **Optimistic Updates:** Use `useMutation` with `onMutate` to eagerly update the UI before the server responds. Always handle rollbacks in `onError` using the context from `onMutate`.
   - **Query Invalidation:** After a successful mutation, invalidate related queries using `queryClient.invalidateQueries({ queryKey: [...] })` to ensure fresh server state.
8. **Caching Strategies**
   - **staleTime vs gcTime:** Understand the difference between `staleTime` (when data becomes stale and needs background refetching) and `gcTime` (how long inactive cache data lives in memory). Use `staleTime` proactively (e.g., `staleTime: 1000 * 60 * 5` for 5 mins) to prevent over-fetching.
9. **Error Handling**
   - **Error Boundaries:** Use TanStack Query's `throwOnError` option (or rely on `useSuspenseQuery`) combined with React Error Boundaries to centralize error handling instead of manually checking `isError` in every component.
