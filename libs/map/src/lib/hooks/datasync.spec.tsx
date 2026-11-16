import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import axios from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MapEventResponse } from '@hermes/util-types';

import { MapConfigProvider } from '../config-context';
import type { MapConfig } from '../config-context';
import { useMapStore } from '../store/store';
import { useMapDataSync } from './datasync';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const CONFIG: MapConfig = {
  baseUrl: 'https://api.hermes.test',
  apiVer: 'v2',
  mapboxToken: 'pk.test-token',
};

const getMock = vi.mocked(axios.get);

function makeEvent(id: string): MapEventResponse {
  return {
    id,
    ai_headline: `Headline ${id}`,
    category: 'CONFLICT',
    category_color: '#ffb454',
    location_name: 'Test location',
    latitude: 10,
    longitude: 20,
    trending_score: 80,
    article_count: 3,
  };
}

function createWrapper(client: QueryClient) {
  return function Wrapper({
    children,
  }: {
    children: React.ReactNode;
  }): React.JSX.Element {
    return (
      <MapConfigProvider config={CONFIG}>
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      </MapConfigProvider>
    );
  };
}

function renderDataSync(): ReturnType<typeof renderHook<ReturnType<typeof useMapDataSync>, unknown>> {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return renderHook(() => useMapDataSync(), { wrapper: createWrapper(client) });
}

describe('useMapDataSync', () => {
  beforeEach(() => {
    getMock.mockReset();
    useMapStore.setState({
      selectedEventId: null,
      selectedEventLngLat: null,
      viewport: null,
      isTlMode: false,
      tlTargetId: null,
      citedEvents: [],
      focusRequest: null,
    });
  });

  it('stays idle until a viewport is available', () => {
    const { result } = renderDataSync();

    expect(result.current.fetchStatus).toBe('idle');
    expect(getMock).not.toHaveBeenCalled();
  });

  it('queries the bbox endpoint with the current viewport', async () => {
    const events = [makeEvent('evt-1'), makeEvent('evt-2')];
    getMock.mockResolvedValue({ data: events });
    useMapStore.setState({
      viewport: { north: 45, south: 30, east: -70, west: -100 },
    });

    const { result } = renderDataSync();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMock).toHaveBeenCalledWith(
      'https://api.hermes.test/api/v2/events/bbox',
      { params: { north: 45, south: 30, east: -70, west: -100 } },
    );
    expect(result.current.data).toEqual(events);
  });

  it('clamps out-of-range coordinates before calling the API', async () => {
    getMock.mockResolvedValue({ data: [] });
    useMapStore.setState({
      viewport: { north: 120, south: -120, east: 250, west: -400 },
    });

    const { result } = renderDataSync();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMock).toHaveBeenCalledWith(
      'https://api.hermes.test/api/v2/events/bbox',
      { params: { north: 90, south: -90, east: 180, west: -180 } },
    );
  });

  it('surfaces transport failures as query errors', async () => {
    getMock.mockRejectedValue(new Error('network down'));
    useMapStore.setState({
      viewport: { north: 1, south: 0, east: 1, west: 0 },
    });

    const { result } = renderDataSync();

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.data).toBeUndefined();
  });
});
