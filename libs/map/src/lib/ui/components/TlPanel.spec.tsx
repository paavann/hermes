import { act, fireEvent, render, screen } from '@testing-library/react';
import type { FeatureCollection } from 'geojson';
import type { Map as MapboxMap, MapLayerMouseEvent } from 'mapbox-gl';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { TlResponse } from '@hermes/util-types';

import { useMapStore } from '../../store/store';
import { useTl } from '../../hooks/useTl';
import { TlPanel } from './TlPanel';

vi.mock('../../hooks/useTl', () => ({
  useTl: vi.fn(),
}));

const useTlMock = vi.mocked(useTl);

const READY: TlResponse = {
  status: 'READY',
  message: null,
  nodes: [
    {
      id: 'node-old',
      date: '2019-03-15T00:00:00Z',
      headline: 'Origin incident',
      summary: 'The first recorded signal.',
      location_name: 'Seattle',
      latitude: 47.6062,
      longitude: -122.3321,
      category_color: null,
    },
    {
      id: 'node-mid',
      date: '2021-07-04T00:00:00Z',
      headline: 'Mid incident',
      summary: 'The lineage escalates.',
      location_name: null,
      latitude: 40.7128,
      longitude: -74.006,
      category_color: null,
    },
    {
      id: 'node-current',
      date: '2026-11-16T00:00:00Z',
      headline: 'Current event',
      summary: 'The event under analysis.',
      location_name: 'New York',
      latitude: null,
      longitude: null,
      category_color: '#22c55e',
    },
  ],
  edges: [
    {
      source_node_id: 'node-old',
      target_node_id: 'node-mid',
      relationship: 'escalated',
    },
    {
      source_node_id: 'node-mid',
      target_node_id: 'node-current',
      relationship: 'triggered',
    },
  ],
  tl_summary: 'A causal chain from origin to present.',
  generated_at: '2026-11-16T00:00:00Z',
};

function mockTl(overrides: {
  data?: TlResponse | null;
  isLoading?: boolean;
  isError?: boolean;
  isRegenerating?: boolean;
  regenerate?: () => void;
} = {}): void {
  useTlMock.mockReturnValue({
    query: {
      data: overrides.data ?? null,
      isLoading: overrides.isLoading ?? false,
      isError: overrides.isError ?? false,
    },
    regenerate: overrides.regenerate ?? vi.fn(),
    isRegenerating: overrides.isRegenerating ?? false,
  } as unknown as ReturnType<typeof useTl>);
}

const sourceIds = new Set<string>();
const layerIds = new Set<string>();
const nodeClickHandlers: Array<(event: MapLayerMouseEvent) => void> = [];
const scrollIntoView = vi.fn<() => void>();

const sourceSetData = vi.fn<(data: FeatureCollection) => void>();
const addSource = vi.fn((id: string) => {
  sourceIds.add(id);
});
const removeSource = vi.fn((id: string) => {
  sourceIds.delete(id);
});
const getSource = vi.fn((id: string) =>
  sourceIds.has(id) ? { setData: sourceSetData } : undefined,
);
const addLayer = vi.fn((layer: { id: string }) => {
  layerIds.add(layer.id);
});
const removeLayer = vi.fn((id: string) => {
  layerIds.delete(id);
});
const getLayer = vi.fn((id: string) => (layerIds.has(id) ? { id } : undefined));
const flyTo = vi.fn();
const setPaintProperty = vi.fn();
const queryRenderedFeatures = vi.fn(() => []);
const getCanvas = vi.fn(() => ({ style: { cursor: '' } }));
const on = vi.fn(
  (
    event: string,
    layerOrHandler?: string | ((event: MapLayerMouseEvent) => void),
    handler?: (event: MapLayerMouseEvent) => void,
  ): void => {
    if (
      event === 'click' &&
      layerOrHandler === 'tl-nodes-layer' &&
      handler !== undefined
    ) {
      nodeClickHandlers.push(handler);
    }
  },
);
const off = vi.fn();

const map = {
  addLayer,
  addSource,
  flyTo,
  getCanvas,
  getLayer,
  getSource,
  off,
  on,
  queryRenderedFeatures,
  removeLayer,
  removeSource,
  setPaintProperty,
} as unknown as MapboxMap;

describe('TlPanel', () => {
  beforeEach(() => {
    sourceIds.clear();
    layerIds.clear();
    nodeClickHandlers.length = 0;
    scrollIntoView.mockClear();
    Element.prototype.scrollIntoView = scrollIntoView;
    useMapStore.setState({
      isTlMode: true,
      tlTargetId: 'evt-1',
      selectedEventId: null,
      selectedEventLngLat: null,
    });
    mockTl();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders a READY timeline newest-first with summary and citations', () => {
    mockTl({ data: READY });

    render(<TlPanel map={map} />);

    expect(screen.getByText('TIMELINE')).toBeTruthy();
    expect(screen.getByText('CAUSAL LINEAGE')).toBeTruthy();
    expect(screen.getByText('LINEAGE SUMMARY')).toBeTruthy();
    expect(
      screen.getByText('A causal chain from origin to present.'),
    ).toBeTruthy();

    const headlines = screen
      .getAllByRole('heading', { level: 3 })
      .map((heading) => heading.textContent);
    expect(headlines).toEqual([
      'Current event',
      'Mid incident',
      'Origin incident',
    ]);

    expect(screen.getByText('Mar 15, 2019')).toBeTruthy();
    expect(screen.getByText('Seattle')).toBeTruthy();
    expect(screen.getByText('Wikipedia')).toBeTruthy();
  });

  it('shows the generating state and disables REFRESH', () => {
    mockTl({ data: { ...READY, status: 'GENERATING' }, isRegenerating: true });

    render(<TlPanel map={map} />);

    expect(screen.getByText('GENERATING TIMELINE...')).toBeTruthy();
    const refresh = screen.getByRole('button', { name: 'REFRESH' });
    expect((refresh as HTMLButtonElement).disabled).toBe(true);
  });

  it('shows the empty-state message for NO_CONTENT', () => {
    mockTl({ data: { ...READY, status: 'NO_CONTENT', nodes: [] } });

    render(<TlPanel map={map} />);

    expect(screen.getByText(/NO HISTORICAL CONTEXT FOUND/)).toBeTruthy();
    expect(screen.getByText('(INSUFFICIENT DATA ON WIKIPEDIA)')).toBeTruthy();
  });

  it('shows the error state for FAILED timelines', () => {
    mockTl({ data: { ...READY, status: 'FAILED', nodes: [] } });

    render(<TlPanel map={map} />);

    expect(screen.getByText('ERROR GENERATING TIMELINE.')).toBeTruthy();
  });

  it('calls regenerate when REFRESH is pressed', () => {
    const regenerate = vi.fn();
    mockTl({ data: READY, regenerate });

    render(<TlPanel map={map} />);

    fireEvent.click(screen.getByRole('button', { name: 'REFRESH' }));

    expect(regenerate).toHaveBeenCalledTimes(1);
  });

  it('exits timeline mode through the close control', () => {
    mockTl({ data: READY });

    render(<TlPanel map={map} />);

    fireEvent.click(screen.getByRole('button', { name: 'Exit timeline' }));

    expect(useMapStore.getState().isTlMode).toBe(false);
    expect(useMapStore.getState().tlTargetId).toBeNull();
  });

  it('adds timeline layers and wires map listeners, then cleans them up', () => {
    mockTl({ data: READY });

    const { unmount } = render(<TlPanel map={map} />);

    expect(addSource).toHaveBeenCalledWith(
      'tl-edges-source',
      expect.objectContaining({ type: 'geojson' }),
    );
    expect(addSource).toHaveBeenCalledWith(
      'tl-nodes-source',
      expect.objectContaining({ type: 'geojson' }),
    );
    expect(addLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'tl-edges-layer', type: 'line' }),
    );
    expect(addLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'tl-nodes-layer', type: 'circle' }),
    );
    expect(on).toHaveBeenCalledWith('click', 'tl-nodes-layer', expect.any(Function));
    expect(on).toHaveBeenCalledWith('mouseenter', 'tl-nodes-layer', expect.any(Function));
    expect(nodeClickHandlers).toHaveLength(1);

    const payloads = sourceSetData.mock.calls.map(([data]) => data);
    const nodesPayload = payloads.find(
      (payload) =>
        payload.features.length === 2 &&
        payload.features.every((feature) => feature.geometry.type === 'Point'),
    );
    expect(nodesPayload?.features[0].geometry).toEqual({
      type: 'Point',
      coordinates: [-122.3321, 47.6062],
    });

    const edgesPayload = payloads.find(
      (payload) =>
        payload.features.length === 1 &&
        payload.features[0].geometry.type === 'LineString',
    );
    expect(edgesPayload?.features[0].properties).toEqual({ type: 'escalated' });

    unmount();

    expect(off).toHaveBeenCalledWith('click', 'tl-nodes-layer', expect.any(Function));
    expect(removeLayer).toHaveBeenCalledWith('tl-nodes-layer');
    expect(removeLayer).toHaveBeenCalledWith('tl-edges-layer');
    expect(removeSource).toHaveBeenCalledWith('tl-nodes-source');
    expect(removeSource).toHaveBeenCalledWith('tl-edges-source');
  });

  it('flies to a node and highlights it when a timeline entry is clicked', () => {
    mockTl({ data: READY });

    render(<TlPanel map={map} />);

    const node = screen.getByRole('button', { name: /Origin incident/ });
    fireEvent.click(node);

    expect(flyTo).toHaveBeenCalledWith({
      center: [-122.3321, 47.6062],
      zoom: 6,
      duration: 1500,
    });
    expect(node.className).toContain('border-neon-blue');
    expect(scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'center',
    });
    expect(setPaintProperty).toHaveBeenCalledWith('tl-nodes-layer', 'circle-opacity', [
      'case',
      ['==', ['get', 'id'], 'node-old'],
      1,
      0.3,
    ]);
  });

  it('activates a node when the map layer emits a click', () => {
    mockTl({ data: READY });

    render(<TlPanel map={map} />);

    act(() => {
      nodeClickHandlers[0]({
        features: [{ properties: { id: 'node-mid' } }],
      } as unknown as MapLayerMouseEvent);
    });

    expect(
      screen.getByRole('button', { name: /Mid incident/ }).className,
    ).toContain('border-neon-blue');
  });

  it('does not attach map handlers when no map instance is supplied', () => {
    mockTl({ data: READY });

    render(<TlPanel map={null} />);

    expect(on).not.toHaveBeenCalled();
    expect(addSource).not.toHaveBeenCalled();
  });
});
