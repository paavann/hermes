import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import axios from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EventDetailResponse } from '@hermes/util-types';

import { MapConfigProvider } from '../config-context';
import type { MapConfig } from '../config-context';
import { useEventDetails } from './eventDetails';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const CONFIG: MapConfig = {
  baseUrl: 'https://api.hermes.test',
  apiVer: 'v1',
  mapboxToken: 'pk.test-token',
};

const getMock = vi.mocked(axios.get);

const EVENT: EventDetailResponse = {
  id: 'evt-42',
  ai_headline: 'Escalation reported',
  ai_summary: 'A detailed summary of the escalation.',
  category: 'CONFLICT',
  category_color: '#ffb454',
  location_name: 'Kyiv',
  trending_score: 91,
  article_count: 4,
  status: 'ACTIVE',
  first_reported_at: '2026-11-01T08:00:00Z',
  last_updated_at: '2026-11-02T09:00:00Z',
  has_lineage: true,
  articles: [
    {
      id: 'art-1',
      title: 'Report',
      url: 'https://example.com/report',
      source_name: 'Example',
      published_at: '2026-11-01T08:00:00Z',
    },
  ],
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

function renderDetails(eventId: string | null) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return renderHook(() => useEventDetails(eventId), {
    wrapper: createWrapper(client),
  });
}

describe('useEventDetails', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('does not request details without an event id', () => {
    const { result } = renderDetails(null);

    expect(result.current.fetchStatus).toBe('idle');
    expect(getMock).not.toHaveBeenCalled();
  });

  it('fetches the event detail endpoint and returns the payload', async () => {
    getMock.mockResolvedValue({ data: EVENT });

    const { result } = renderDetails('evt-42');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getMock).toHaveBeenCalledWith(
      'https://api.hermes.test/api/v1/events/evt-42',
    );
    expect(result.current.data?.ai_summary).toBe(
      'A detailed summary of the escalation.',
    );
  });

  it('reports failures without retrying by default in the test client', async () => {
    getMock.mockRejectedValue(new Error('not found'));

    const { result } = renderDetails('evt-missing');

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(getMock).toHaveBeenCalledTimes(1);
  });
});
