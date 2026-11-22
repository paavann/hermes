import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen } from '@testing-library/react';
import type { FeatureCollection } from 'geojson';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { MapEventResponse } from '@hermes/util-types';

import { MapConfigProvider } from '../config-context';
import type { MapConfig } from '../config-context';
import { useMapDataSync } from '../hooks/datasync';
import { useMapStore } from '../store/store';
import { MapView } from './map-view';

vi.mock('../hooks/datasync', () => ({
  useMapDataSync: vi.fn(),
}));

vi.mock('../hooks/eventDetails', () => ({
  useEventDetails: vi.fn(() => ({
    data: null,
    isLoading: false,
    isError: false,
  })),
}));

const mapbox = vi.hoisted(() => {
  interface FakeHandler {
    (...args: unknown[]): void;
  }

  interface FakeMapInstance {
    options: Record<string, unknown>;
    handlers: Map<string, FakeHandler[]>;
    setData: ReturnType<typeof vi.fn>;
    on: ReturnType<typeof vi.fn>;
    once: ReturnType<typeof vi.fn>;
    off: ReturnType<typeof vi.fn>;
    getCanvas: ReturnType<typeof vi.fn>;
    getBounds: ReturnType<typeof vi.fn>;
    getSource: ReturnType<typeof vi.fn>;
    addSource: ReturnType<typeof vi.fn>;
    removeSource: ReturnType<typeof vi.fn>;
    getLayer: ReturnType<typeof vi.fn>;
    addLayer: ReturnType<typeof vi.fn>;
    removeLayer: ReturnType<typeof vi.fn>;
    setLayoutProperty: ReturnType<typeof vi.fn>;
    setPaintProperty: ReturnType<typeof vi.fn>;
    isStyleLoaded: ReturnType<typeof vi.fn>;
    queryRenderedFeatures: ReturnType<typeof vi.fn>;
    project: ReturnType<typeof vi.fn>;
    easeTo: ReturnType<typeof vi.fn>;
    flyTo: ReturnType<typeof vi.fn>;
    getZoom: ReturnType<typeof vi.fn>;
    remove: ReturnType<typeof vi.fn>;
  }

  const instances: FakeMapInstance[] = [];

  const module = {
    accessToken: '',
    Map: vi.fn(function (options: Record<string, unknown>) {
      const handlers = new Map<string, FakeHandler[]>();
      const sources = new Set<string>();
      const layers = new Set<string>();
      const setData = vi.fn();

      const register = (event: string, args: unknown[]): void => {
        const handler = args.at(-1);
        if (typeof handler === 'function') {
          const list = handlers.get(event) ?? [];
          list.push(handler as FakeHandler);
          handlers.set(event, list);
        }
      };

      const instance: FakeMapInstance = {
        options,
        handlers,
        setData,
        on: vi.fn((event: string, ...args: unknown[]) => register(event, args)),
        once: vi.fn((event: string, ...args: unknown[]) => register(event, args)),
        off: vi.fn(),
        getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
        getBounds: vi.fn(() => ({
          getNorthEast: () => ({ lat: 40, lng: 20 }),
          getSouthWest: () => ({ lat: 10, lng: -10 }),
        })),
        getSource: vi.fn((id: string) =>
          sources.has(id)
            ? { setData, getClusterExpansionZoom: vi.fn() }
            : undefined,
        ),
        addSource: vi.fn((id: string, _spec?: unknown) => {
          sources.add(id);
        }),
        removeSource: vi.fn((id: string) => {
          sources.delete(id);
        }),
        getLayer: vi.fn((id: string) => (layers.has(id) ? { id } : undefined)),
        addLayer: vi.fn((layer: { id: string }) => {
          layers.add(layer.id);
        }),
        removeLayer: vi.fn((id: string) => {
          layers.delete(id);
        }),
        setLayoutProperty: vi.fn(),
        setPaintProperty: vi.fn(),
        isStyleLoaded: vi.fn(() => true),
        queryRenderedFeatures: vi.fn(() => []),
        project: vi.fn(() => ({ x: 0, y: 0 })),
        easeTo: vi.fn(),
        flyTo: vi.fn(),
        getZoom: vi.fn(() => 2),
        remove: vi.fn(),
      };

      instances.push(instance);
      return instance;
    }),
  };

  return { module, instances };
});

vi.mock('mapbox-gl', () => ({
  default: mapbox.module,
}));

const CONFIG: MapConfig = {
  baseUrl: 'https://api.hermes.test',
  apiVer: 'v1',
  mapboxToken: 'pk.test-token',
};

const EVENTS: MapEventResponse[] = [
  {
    id: 'event-a',
    ai_headline: 'Lower ranked duplicate',
    category: 'CONFLICT',
    category_color: '#ffb454',
    location_name: null,
    latitude: 10.123456,
    longitude: 20.654321,
    importance_score: 40,
    verification_status: 'SINGLE_SOURCE',
    selection_tier: 'FILLER',
    impact_level: 'MINOR',
    scope: 'LOCAL',
    event_time: null,
    article_count: 1,
    source_count: 1,
    family_count: 1,
    independent_origin_count: 1,
    thread_id: null,
  },
  {
    id: 'event-b',
    ai_headline: 'Higher ranked duplicate',
    category: 'CONFLICT',
    category_color: '#ffb454',
    location_name: null,
    latitude: 10.123456,
    longitude: 20.654321,
    importance_score: 90,
    verification_status: 'CONFIRMED',
    selection_tier: 'PRIMARY',
    impact_level: 'CRITICAL',
    scope: 'COUNTRY',
    event_time: null,
    article_count: 3,
    source_count: 3,
    family_count: 3,
    independent_origin_count: 3,
    thread_id: null,
  },
  {
    id: 'event-c',
    ai_headline: 'Distinct location',
    category: 'HEALTH',
    category_color: '#f472b6',
    location_name: null,
    latitude: 11,
    longitude: 21,
    importance_score: 60,
    verification_status: 'CORROBORATED',
    selection_tier: 'PRIMARY',
    impact_level: 'MODERATE',
    scope: 'CITY',
    event_time: null,
    article_count: 2,
    source_count: 2,
    family_count: 2,
    independent_origin_count: 2,
    thread_id: null,
  },
];

const useMapDataSyncMock = vi.mocked(useMapDataSync);

function renderMapView(): ReturnType<typeof render> {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <MapConfigProvider config={CONFIG}>
      <QueryClientProvider client={client}>
        <MapView />
      </QueryClientProvider>
    </MapConfigProvider>,
  );
}

function emit(event: string): void {
  const instance = mapbox.instances[0];
  const handlers = instance?.handlers.get(event) ?? [];
  act(() => {
    handlers.forEach((handler) => handler());
  });
}

describe('MapView', () => {
  beforeEach(() => {
    mapbox.instances.length = 0;
    mapbox.module.accessToken = '';
    useMapDataSyncMock.mockReturnValue({
      data: EVENTS,
      isFetching: false,
    } as unknown as ReturnType<typeof useMapDataSync>);
    useMapStore.setState({
      viewport: null,
      selectedEventId: null,
      selectedEventLngLat: null,
      isTlMode: false,
      tlTargetId: null,
      citedEvents: [],
      focusRequest: null,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('creates the Mapbox map from the injected config and syncs bounds', () => {
    renderMapView();

    const instance = mapbox.instances[0];
    expect(instance).toBeDefined();
    expect(mapbox.module.accessToken).toBe('pk.test-token');
    expect(mapbox.module.Map).toHaveBeenCalledWith(
      expect.objectContaining({
        container: expect.any(HTMLDivElement),
        center: [0, 20],
        zoom: 1.5,
        projection: 'mercator',
        maxPitch: 0,
        dragRotate: false,
        touchPitch: false,
        attributionControl: false,
        renderWorldCopies: false,
      }),
    );

    emit('moveend');

    expect(useMapStore.getState().viewport).toEqual({
      north: 40,
      south: 10,
      east: 20,
      west: -10,
    });
  });

  it('adds clustered event layers and keeps every event pin', () => {
    renderMapView();

    emit('load');
    const instance = mapbox.instances[0];

    expect(instance.addSource).toHaveBeenCalledWith(
      'events-source',
      expect.objectContaining({
        type: 'geojson',
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      }),
    );
    expect(instance.addSource).toHaveBeenCalledWith(
      'cited-events-source',
      expect.objectContaining({ type: 'geojson' }),
    );
    expect(instance.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'hermes-clusters', source: 'events-source' }),
    );
    expect(instance.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'hermes-unclustered-point',
        source: 'events-source',
      }),
    );
    expect(instance.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'hermes-cited-points' }),
    );

    const eventsCall = instance.addSource.mock.calls.find(
      ([id]) => id === 'events-source',
    );
    const spec = eventsCall?.[1] as
      | { data: FeatureCollection }
      | undefined;
    expect(spec?.data.features).toHaveLength(3);
    expect(spec?.data.features[0].properties?.id).toBe('event-b');
    expect(spec?.data.features[0].properties?.rank).toBe(1);
    expect(spec?.data.features[1].properties?.id).toBe('event-c');
    expect(spec?.data.features[2].properties?.id).toBe('event-a');
  });

  it('shows the sync loader while fetching and swaps to the timeline panel', () => {
    useMapDataSyncMock.mockReturnValue({
      data: EVENTS,
      isFetching: true,
    } as unknown as ReturnType<typeof useMapDataSync>);

    renderMapView();
    emit('load');

    expect(screen.getByText('SYNCING')).toBeTruthy();

    act(() => {
      useMapStore.getState().setTlMode(true);
    });

    expect(screen.getByText('TIMELINE')).toBeTruthy();
    expect(screen.queryByText('SYNCING')).toBeNull();

    const instance = mapbox.instances[0];
    expect(instance.setLayoutProperty).toHaveBeenCalledWith(
      'hermes-unclustered-point',
      'visibility',
      'none',
    );
    expect(instance.setLayoutProperty).toHaveBeenCalledWith(
      'hermes-cited-points',
      'visibility',
      'none',
    );
  });

  it('flies to the focused event when a focus request is issued', () => {
    renderMapView();
    emit('load');

    act(() => {
      useMapStore.getState().focusEvent('event-a', [12.5, 34.5]);
    });

    expect(mapbox.instances[0].flyTo).toHaveBeenCalledWith({
      center: [12.5, 34.5],
      zoom: 6,
      duration: 1200,
      essential: true,
    });
  });

  it('removes the map instance on unmount', () => {
    const { unmount } = renderMapView();

    unmount();

    expect(mapbox.instances[0].remove).toHaveBeenCalledTimes(1);
  });
});
