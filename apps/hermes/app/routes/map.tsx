import { lazy, Suspense, useCallback } from 'react';
import type { LoaderFunctionArgs } from 'react-router';
import { getAuth } from '@clerk/react-router/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { CornerReticle, HermesWordmark } from '@hermes/ui-components';
import type { ChatSource } from '@hermes/util-types';

import { citedEventsFromSources } from '../components/map/cited-sources';
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
 * Dynamic client-only boundary for MapView, ChatPanel, and their providers.
 * Shielding @hermes/map and @hermes/chat behind React.lazy ensures Mapbox GL JS
 * and browser-only chat APIs are never evaluated in Node.js server environments
 * during SSR.
 */
const DynamicMapContainer = lazy(async () => {
  const [
    { MapView, MapConfigProvider, useMapStore },
    { ChatConfigProvider, ChatPanel },
  ] = await Promise.all([import('@hermes/map'), import('@hermes/chat')]);

  function MapWithChat(): React.JSX.Element {
    const selectedEventId = useMapStore((state) => state.selectedEventId);
    const viewport = useMapStore((state) => state.viewport);
    const isTimelineMode = useMapStore((state) => state.isTlMode);
    const focusEvent = useMapStore((state) => state.focusEvent);
    const setCitedEvents = useMapStore((state) => state.setCitedEvents);

    const handleSources = useCallback(
      (sources: ChatSource[]) => {
        setCitedEvents(citedEventsFromSources(sources));
      },
      [setCitedEvents],
    );

    const handleCitationActivate = useCallback(
      (source: ChatSource) => {
        if (
          source.event_id === null ||
          source.latitude === null ||
          source.longitude === null
        ) {
          return;
        }
        focusEvent(source.event_id, [source.longitude, source.latitude]);
      },
      [focusEvent],
    );

    return (
      <MapConfigProvider config={MAP_CONFIG}>
        <ChatConfigProvider
          config={{ baseUrl: MAP_CONFIG.baseUrl, apiVer: MAP_CONFIG.apiVer }}
        >
          <MapView />
          <div hidden={isTimelineMode}>
            <ChatPanel
              autoScope={{ eventId: selectedEventId, viewport }}
              onSources={handleSources}
              onCitationActivate={handleCitationActivate}
            />
          </div>
        </ChatConfigProvider>
      </MapConfigProvider>
    );
  }

  return {
    default: MapWithChat,
  };
});

/**
 * Minimal loading screen displayed during SSR hydration
 * and while Mapbox GL JS initializes.
 */
export function MapLoadingFallback(): React.JSX.Element {
  return (
    <div
      className="relative flex h-dvh w-full select-none items-center justify-center overflow-hidden bg-black font-mono"
      role="status"
      aria-live="polite"
    >
      <div
        className="pointer-events-none absolute inset-0 bg-grid-hud opacity-50"
        aria-hidden="true"
      />
      <CornerReticle className="inset-6" tone="bone" size="lg" />

      <div className="relative flex flex-col items-center gap-5">
        <HermesWordmark className="w-40 text-bone/35" />
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-slate-muted">
          <span className="h-1.5 w-1.5 animate-pulse bg-neon-blue" aria-hidden="true" />
          <span>LOADING LIVE MAP</span>
        </div>
        <div className="h-px w-48 overflow-hidden bg-border-subtle" aria-hidden="true">
          <div className="h-full w-1/3 animate-pulse bg-neon-blue" />
        </div>
      </div>
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
      </main>
    </QueryClientProvider>
  );
}

