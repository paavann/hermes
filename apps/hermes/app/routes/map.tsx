import { lazy, Suspense } from 'react';
import type { LoaderFunctionArgs } from 'react-router';
import { getAuth } from '@clerk/react-router/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { LiveClock } from '@hermes/ui-components';

import type { Route } from './+types/map';

export async function loader(args: LoaderFunctionArgs) {
  const { userId } = await getAuth(args);
  return { userId: userId ?? null };
}

const queryClient = new QueryClient();

const MAP_CONFIG = {
  baseUrl: import.meta.env.VITE_BASE_URL,
  apiVer: import.meta.env.VITE_API_VER,
  mapboxToken: import.meta.env.VITE_MAPBOX_TOKEN,
};

export const meta: Route.MetaFunction = () => [
  { title: 'Hermes — Live Intelligence Map' },
  { name: 'description', content: 'Real-time geospatial news intelligence. Monitor global events as they unfold.' },
];

/**
 * Dynamic client-only boundary for MapView and MapConfigProvider.
 * Shielding @hermes/map behind React.lazy ensures Mapbox GL JS is never evaluated
 * in Node.js server environments during SSR.
 */
const DynamicMapContainer = lazy(async () => {
  const { MapView, MapConfigProvider } = await import('@hermes/map');
  return {
    default: function DynamicMap(): React.JSX.Element {
      return (
        <MapConfigProvider config={MAP_CONFIG}>
          <MapView />
        </MapConfigProvider>
      );
    },
  };
});

/**
 * Minimal loading screen displayed during SSR hydration
 * and while Mapbox GL JS initializes.
 */
export function MapLoadingFallback(): React.JSX.Element {
  return (
    <div
      className="relative w-full h-dvh overflow-hidden bg-black flex items-center justify-center font-mono select-none"
      role="status"
      aria-live="polite"
    >
      <span className="text-xs uppercase tracking-widest text-slate-muted animate-pulse">
        Loading Map...
      </span>
    </div>
  );
}

export function HydrateFallback(): React.JSX.Element {
  return <MapLoadingFallback />;
}

export default function MapRoute(): React.JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <main className="relative w-full h-dvh overflow-hidden bg-black">
        <Suspense fallback={<MapLoadingFallback />}>
          <DynamicMapContainer />
        </Suspense>
        <LiveClock />
      </main>
    </QueryClientProvider>
  );
}

