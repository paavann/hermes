import { lazy, Suspense } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { LiveClock } from '@hermes/ui-components';

import type { Route } from './+types/map';

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
 * Tactical monospace loading skeleton rendered on the server during SSR
 * and displayed in the browser while Mapbox GL JS initializes.
 */
export function TacticalMapSkeleton(): React.JSX.Element {
  return (
    <div
      className="relative w-full h-dvh overflow-hidden bg-black flex flex-col items-center justify-center font-mono select-none"
      role="status"
      aria-live="polite"
    >
      <div className="border border-hud-border bg-hud-bg/80 backdrop-blur-md px-6 py-4 max-w-md w-full mx-4 shadow-[0_0_20px_rgba(0,240,255,0.1)]">
        <div className="flex items-center justify-between border-b border-hud-border/60 pb-2 mb-3">
          <span className="text-neon-blue text-xs uppercase tracking-widest flex items-center gap-2">
            <span className="inline-block w-2 h-2 bg-neon-blue animate-pulse" />
            Hermes // Core Terminal
          </span>
          <span className="text-xs text-neutral-400">GEO.LOCK</span>
        </div>
        <p className="text-xs text-neutral-300 tracking-wider">
          INITIALIZING SATELLITE TELEMETRY...
        </p>
        <div className="mt-3 w-full bg-neutral-900 h-1 overflow-hidden">
          <div className="h-full bg-neon-blue animate-pulse w-2/3" />
        </div>
        <div className="mt-3 flex justify-between text-[10px] text-neutral-400 uppercase">
          <span>WebGL Engine: Standby</span>
          <span>SRID: 4326</span>
        </div>
      </div>
    </div>
  );
}

export function HydrateFallback(): React.JSX.Element {
  return <TacticalMapSkeleton />;
}

export default function MapRoute(): React.JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <main className="relative w-full h-dvh overflow-hidden bg-black">
        <Suspense fallback={<TacticalMapSkeleton />}>
          <DynamicMapContainer />
        </Suspense>
        <LiveClock />
      </main>
    </QueryClientProvider>
  );
}

