import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import axios from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { TlResponse } from '@hermes/util-types';

import { MapConfigProvider } from '../config-context';
import type { MapConfig } from '../config-context';
import { useTl } from './useTl';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const CONFIG: MapConfig = {
  baseUrl: 'https://api.hermes.test',
  apiVer: 'v3',
  mapboxToken: 'pk.test-token',
};

const postMock = vi.mocked(axios.post);

const GENERATING: TlResponse = {
  status: 'GENERATING',
  message: 'Working',
  nodes: [],
  edges: [],
  tl_summary: null,
  generated_at: null,
};

const READY: TlResponse = {
  status: 'READY',
  message: null,
  nodes: [
    {
      id: 'node-1',
      date: '2020-01-01T00:00:00Z',
      headline: 'Origin',
      summary: 'Where it started.',
      location_name: 'Seattle',
      latitude: 47.6062,
      longitude: -122.3321,
      category_color: null,
    },
  ],
  edges: [],
  tl_summary: 'A short lineage.',
  generated_at: '2026-11-16T00:00:00Z',
};

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

function renderTl(eventId: string | null) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return renderHook(() => useTl(eventId), { wrapper: createWrapper(client) });
}

describe('useTl', () => {
  beforeEach(() => {
    postMock.mockReset();
  });

  it('skips the request when there is no target event', () => {
    const { result } = renderTl(null);

    expect(result.current.query.fetchStatus).toBe('idle');
    expect(postMock).not.toHaveBeenCalled();
  });

  it('posts to the timeline endpoint and returns the response', async () => {
    postMock.mockResolvedValue({ data: READY });

    const { result } = renderTl('evt-7');

    await waitFor(() => expect(result.current.query.isSuccess).toBe(true));

    expect(postMock).toHaveBeenCalledWith(
      'https://api.hermes.test/api/v3/events/tl/evt-7',
    );
    expect(result.current.query.data?.status).toBe('READY');
    expect(result.current.query.data?.tl_summary).toBe('A short lineage.');
  });

  it('regenerates with force_refresh and replaces the cached timeline', async () => {
    postMock
      .mockResolvedValueOnce({ data: GENERATING })
      .mockResolvedValueOnce({ data: READY });

    const { result } = renderTl('evt-7');

    await waitFor(() =>
      expect(result.current.query.data?.status).toBe('GENERATING'),
    );

    act(() => {
      result.current.regenerate();
    });

    await waitFor(() => expect(result.current.query.data?.status).toBe('READY'));
    await waitFor(() => expect(result.current.isRegenerating).toBe(false));

    expect(postMock).toHaveBeenLastCalledWith(
      'https://api.hermes.test/api/v3/events/tl/evt-7?force_refresh=true',
    );
    expect(result.current.query.data?.nodes).toHaveLength(1);
  });

  it('does not regenerate without a target event', async () => {
    const { result } = renderTl(null);

    act(() => {
      result.current.regenerate();
    });

    await waitFor(() => expect(result.current.isRegenerating).toBe(false));

    expect(postMock).not.toHaveBeenCalled();
    expect(result.current.query.data).toBeNull();
  });
});
