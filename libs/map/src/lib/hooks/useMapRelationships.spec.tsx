import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import axios from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MapRelationshipEdgeResponse } from '@hermes/util-types';

import { MapConfigProvider } from '../config-context';
import type { MapConfig } from '../config-context';
import { useMapStore } from '../store/store';
import { useMapRelationships } from './useMapRelationships';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
  },
}));

const CONFIG: MapConfig = {
  baseUrl: 'https://api.hermes.test',
  apiVer: 'v1',
  mapboxToken: 'pk.test-token',
};

const getMock = vi.mocked(axios.get);

function makeEdge(id: string): MapRelationshipEdgeResponse {
  return {
    id,
    source_event_id: 'evt-china',
    target_event_id: 'evt-pakistan',
    source_headline: 'Pakistani astronaut boards China space station',
    source_category: 'SCIENCE',
    source_category_color: '#a855f7',
    source_location_name: 'China',
    source_latitude: 34.79,
    source_longitude: 103.71,
    target_headline: 'SUPARCO watch party in Islamabad',
    target_category: 'TECHNOLOGY',
    target_category_color: '#00f0ff',
    target_location_name: 'Islamabad',
    target_latitude: 33.6946,
    target_longitude: 73.0646,
    relationship_type: 'REACTION',
    confidence: 0.91,
    rationale: 'Islamabad crowd gathered for the orbital docking.',
  };
}

function renderRelationships(): ReturnType<
  typeof renderHook<ReturnType<typeof useMapRelationships>, unknown>
> {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return renderHook(() => useMapRelationships(), {
    wrapper: ({ children }: { children: React.ReactNode }): React.JSX.Element => (
      <MapConfigProvider config={CONFIG}>
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      </MapConfigProvider>
    ),
  });
}

describe('useMapRelationships', () => {
  beforeEach(() => {
    getMock.mockReset();
    useMapStore.setState({
      viewport: null,
      showRelationships: true,
      isTlMode: false,
      selectedEventId: null,
      selectedEventLngLat: null,
      tlTargetId: null,
      citedEvents: [],
      focusRequest: null,
    });
  });

  it('stays idle until viewport exists and relationships are visible outside timeline mode', () => {
    const noViewport = renderRelationships();
    expect(noViewport.result.current.fetchStatus).toBe('idle');
    noViewport.unmount();

    act(() => {
      useMapStore.setState({
        viewport: { north: 50, south: 20, east: 120, west: 60 },
        showRelationships: false,
      });
    });
    const toggledOff = renderRelationships();
    expect(toggledOff.result.current.fetchStatus).toBe('idle');
    toggledOff.unmount();

    act(() => {
      useMapStore.setState({
        viewport: { north: 50, south: 20, east: 120, west: 60 },
        showRelationships: true,
        isTlMode: true,
      });
    });
    const inTlMode = renderRelationships();
    expect(inTlMode.result.current.fetchStatus).toBe('idle');
    expect(getMock).not.toHaveBeenCalled();
  });

  it('clamps out-of-range coordinates and queries /events/relationships', async () => {
    const edge = makeEdge('edge-1');
    getMock.mockResolvedValue({ data: [edge] });
    useMapStore.setState({
      viewport: { north: 95, south: -95, east: 210, west: -200 },
      showRelationships: true,
      isTlMode: false,
    });

    const { result } = renderRelationships();

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(getMock).toHaveBeenCalledWith(
      'https://api.hermes.test/api/v1/events/relationships',
      {
        params: { north: 90, south: -90, east: 180, west: -180 },
      },
    );
    expect(result.current.data).toEqual([edge]);
  });
});
