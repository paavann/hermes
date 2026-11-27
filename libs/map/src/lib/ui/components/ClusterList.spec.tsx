import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { MapEventResponse } from '@hermes/util-types';

import { ClusterList } from './ClusterList';

function makeEvent(
  id: string,
  headline: string,
  relationshipCount?: number,
): MapEventResponse {
  return {
    id,
    ai_headline: headline,
    category: 'CONFLICT',
    category_color: '#ef4444',
    location_name: 'Pyongyang',
    latitude: 39.03,
    longitude: 125.75,
    importance_score: 44,
    verification_status: 'CORROBORATED',
    selection_tier: 'PRIMARY',
    impact_level: 'MAJOR',
    scope: 'CITY',
    event_time: '2026-11-25T10:00:00Z',
    article_count: 2,
    source_count: 2,
    family_count: 2,
    independent_origin_count: 2,
    relationship_count: relationshipCount,
    thread_id: null,
    thread_name: null,
  };
}

describe('ClusterList', () => {
  it('renders link counts for linked events and omits badge when unlinked', () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();

    render(
      <ClusterList
        events={[
          makeEvent('e1', 'North Korea orders embassy closure', 2),
          makeEvent('e2', 'Separate embassy advisory', 1),
          makeEvent('e3', 'Routine weather brief', 0),
        ]}
        onSelect={onSelect}
        onClose={onClose}
      />,
    );

    expect(screen.getByText('CLUSTER // 3 EVENTS')).toBeTruthy();
    expect(screen.getByText('2 LINKS')).toBeTruthy();
    expect(screen.getByText('1 LINK')).toBeTruthy();
    expect(screen.queryByText('0 LINKS')).toBeNull();

    fireEvent.click(screen.getByText('North Korea orders embassy closure'));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'e1' }),
    );
  });
});
