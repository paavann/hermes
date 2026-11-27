import { render, screen, act, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Map as MapboxMap } from 'mapbox-gl';
import { EventPopup } from './EventPopup';
import { useMapStore } from '../../store/store';
import * as eventDetailsModule from '../../hooks/eventDetails';

vi.mock('../../hooks/eventDetails', () => ({
  useEventDetails: vi.fn(),
}));

describe('EventPopup', () => {
  const mockMap = {
    project: vi.fn().mockReturnValue({ x: 400, y: 300 }),
  } as unknown as MapboxMap;

  const mockCanadaEvent = {
    id: 'event-canada-123',
    title: 'Northern Wildfire Monitoring Initiative',
    ai_headline: 'WILDFIRE RISK ELEVATED IN NORTHWEST TERRITORIES',
    ai_summary: 'Satellite telemetry reports elevated thermal anomalies across the region.',
    location_name: 'Canada',
    latitude: 60.8108,
    longitude: -107.124,
    importance_score: 95,
    score_breakdown: { version: 'score-v1', score: 95 },
    verification_status: 'CONFIRMED',
    selection_tier: 'PRIMARY',
    impact_level: 'MAJOR',
    scope: 'COUNTRY',
    source_count: 1,
    family_count: 1,
    independent_origin_count: 1,
    thread_id: 'thread-wildfire',
    thread_name: 'Canadian wildfire season',
    status: 'ACTIVE',
    event_time: '2026-11-06T11:30:00Z',
    first_reported_at: '2026-11-06T12:00:00Z',
    last_updated_at: '2026-11-06T12:00:00Z',
    category: 'ENVIRONMENT',
    category_color: '#22c55e',
    articles: [
      {
        id: 'art-1',
        title: 'Wildfire Alerts Across Canada - Reuters',
        url: 'https://www.reuters.com/world/americas/wildfire-canada',
        source_name: 'Reuters',
        publish_time: '2026-11-06T12:00:00Z',
      },
    ],
  };

  beforeEach(() => {
    vi.useFakeTimers();
    useMapStore.setState({
      selectedEventId: null,
      selectedEventLngLat: null,
      isTlMode: false,
      tlTargetId: null,
    });
    vi.mocked(eventDetailsModule.useEventDetails).mockReturnValue({
      data: mockCanadaEvent,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof eventDetailsModule.useEventDetails>);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('renders nothing when no event is selected', () => {
    const { container } = render(<EventPopup map={mockMap} />);
    expect(container.firstChild).toBeNull();
  });

  it('opens the story thread from the popup', () => {
    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [-107.124, 60.8108],
    });
    const onThreadOpen = vi.fn();

    render(<EventPopup map={mockMap} onThreadOpen={onThreadOpen} />);

    fireEvent.click(screen.getByRole('button', { name: /story:/i }));

    expect(onThreadOpen).toHaveBeenCalledWith('thread-wildfire');
  });

  it('renders the popup header and location for Canada (60.8108°, -107.1240°)', () => {
    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [-107.124, 60.8108],
    });

    render(<EventPopup map={mockMap} />);

    expect(screen.getByText('OVERVIEW')).toBeTruthy();
    expect(screen.getByText(/Canada • 60\.8108°, -107\.1240°/)).toBeTruthy();
    expect(screen.getByRole('button', { name: /close event overview/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /analyze/i })).toBeTruthy();
  });

  it('closes the popup and sets selectedEventId to null when CLOSE is clicked', () => {
    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [-107.124, 60.8108],
    });

    render(<EventPopup map={mockMap} />);

    const closeBtn = screen.getByRole('button', { name: /close event overview/i });
    fireEvent.click(closeBtn);

    // Button triggers tactile pop animation state
    expect(closeBtn.className).toContain('animate-pop');

    // After 90ms animation timeout, selectedEventId is cleared in store
    act(() => {
      vi.advanceTimersByTime(90);
    });

    expect(useMapStore.getState().selectedEventId).toBeNull();
  });

  it('re-enables CLOSE button when a subsequent event is opened (verifies bugfix for stuck isClosing)', () => {
    // 1. Open first event and close it
    useMapStore.setState({
      selectedEventId: 'event-first-001',
      selectedEventLngLat: [-74.006, 40.7128],
    });

    const { rerender } = render(<EventPopup map={mockMap} />);

    const firstCloseBtn = screen.getByRole('button', { name: /close event overview/i });
    fireEvent.click(firstCloseBtn);

    act(() => {
      vi.advanceTimersByTime(90);
    });

    expect(useMapStore.getState().selectedEventId).toBeNull();

    // 2. Open Canada event as the second event
    act(() => {
      useMapStore.setState({
        selectedEventId: 'event-canada-123',
        selectedEventLngLat: [-107.124, 60.8108],
      });
    });

    rerender(<EventPopup map={mockMap} />);

    // 3. Canada popup should be visible and CLOSE button must work
    const canadaCloseBtn = screen.getByRole('button', { name: /close event overview/i });
    expect(canadaCloseBtn).toBeTruthy();

    fireEvent.click(canadaCloseBtn);

    act(() => {
      vi.advanceTimersByTime(90);
    });

    expect(useMapStore.getState().selectedEventId).toBeNull();
  });

  it('closes the popup when Escape key is pressed', () => {
    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [-107.124, 60.8108],
    });

    render(<EventPopup map={mockMap} />);

    fireEvent.keyDown(window, { key: 'Escape' });

    act(() => {
      vi.advanceTimersByTime(90);
    });

    expect(useMapStore.getState().selectedEventId).toBeNull();
  });

  it('activates timeline mode when ANALYZE is clicked', () => {
    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [-107.124, 60.8108],
    });

    render(<EventPopup map={mockMap} />);

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    fireEvent.click(analyzeBtn);

    expect(analyzeBtn.className).toContain('animate-pop');

    act(() => {
      vi.advanceTimersByTime(90);
    });

    expect(useMapStore.getState().isTlMode).toBe(true);
    expect(useMapStore.getState().tlTargetId).toBe('event-canada-123');
    expect(useMapStore.getState().selectedEventId).toBeNull();
  });

  it('renders connected events and focuses the map when clicked', () => {
    vi.mocked(eventDetailsModule.useEventDetails).mockReturnValue({
      data: {
        ...mockCanadaEvent,
        relationship_count: 1,
        relationships: [
          {
            id: 'rel-1',
            relationship_type: 'REACTION',
            direction: 'OUTGOING',
            confidence: 0.91,
            rationale: 'Crowds watched the orbital boarding.',
            related_event_id: 'event-china-999',
            related_headline: 'Pakistani astronaut boards Tiangong',
            related_category: 'SCIENCE',
            related_category_color: '#a855f7',
            related_location_name: 'China',
            related_latitude: 34.79,
            related_longitude: 103.71,
            related_importance_score: 35,
            related_event_time: '2026-11-25T08:11:00Z',
          },
        ],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof eventDetailsModule.useEventDetails>);

    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [-107.124, 60.8108],
      focusRequest: null,
    });

    render(<EventPopup map={mockMap} />);

    expect(screen.getByText('CONNECTED EVENTS')).toBeTruthy();
    const badgeText = screen.getByText('REACTION →');
    expect(badgeText).toBeTruthy();
    expect(badgeText.parentElement?.style.color).toBe('rgb(255, 79, 216)');
    expect(
      screen.getByText('Pakistani astronaut boards Tiangong'),
    ).toBeTruthy();
    expect(
      screen.getByText('Crowds watched the orbital boarding.'),
    ).toBeTruthy();

    fireEvent.click(
      screen.getByRole('button', {
        name: /pakistani astronaut boards tiangong/i,
      }),
    );

    const state = useMapStore.getState();
    expect(state.selectedEventId).toBe('event-china-999');
    expect(state.selectedEventLngLat).toEqual([103.71, 34.79]);
    expect(state.focusRequest?.eventId).toBe('event-china-999');
  });

  it('omits connected events section when an event has no relationships', () => {
    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [-107.124, 60.8108],
    });

    render(<EventPopup map={mockMap} />);

    expect(screen.queryByText('CONNECTED EVENTS')).toBeNull();
  });

  it('displays retained WHO actors alongside WHERE metadata', () => {
    vi.mocked(eventDetailsModule.useEventDetails).mockReturnValue({
      data: {
        ...mockCanadaEvent,
        location_name: 'Gaza Strip',
        actors: [
          {
            name: 'Israel',
            kind: 'STATE',
            role: 'ACTOR',
            location_name: 'Israel',
            country_code: 'IL',
            latitude: 31.0461,
            longitude: 34.8516,
          },
        ],
        relationship_count: 0,
        relationships: [],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof eventDetailsModule.useEventDetails>);

    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [34.4634, 31.5411],
    });

    render(<EventPopup map={mockMap} />);

    expect(screen.getByText('ACTORS (WHO)')).toBeTruthy();
    expect(screen.getByText('Israel')).toBeTruthy();
    expect(screen.getByText('ACTOR')).toBeTruthy();
    expect(screen.getByText('IL')).toBeTruthy();
    expect(screen.queryByText('CONNECTED EVENTS')).toBeNull();
  });

  it('stops click propagation to outer layers when clicking inside the popup', () => {
    useMapStore.setState({
      selectedEventId: 'event-canada-123',
      selectedEventLngLat: [-107.124, 60.8108],
    });

    const outerClickHandler = vi.fn();
    render(
      <div onClick={outerClickHandler}>
        <EventPopup map={mockMap} />
      </div>,
    );

    const closeBtn = screen.getByRole('button', { name: /close event overview/i });
    fireEvent.click(closeBtn);

    expect(outerClickHandler).not.toHaveBeenCalled();
  });

  it('clamps the popup horizontally outside left rail and open drawer insets', () => {
    const originalWidth = window.innerWidth;
    const originalOffsetWidth = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'offsetWidth',
    );
    const originalOffsetHeight = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'offsetHeight',
    );
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 1280,
    });
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
      configurable: true,
      value: 384,
    });
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
      configurable: true,
      value: 300,
    });

    const westernMap = {
      project: vi.fn().mockReturnValue({ x: 30, y: 300 }),
    } as unknown as MapboxMap;

    try {
      useMapStore.setState({
        selectedEventId: 'event-canada-123',
        selectedEventLngLat: [-122.146, 37.44],
      });

      const { rerender } = render(
        <EventPopup map={westernMap} popupInsets={{ left: 48, right: 0 }} />,
      );
      const region = screen.getByRole('region', { name: 'Event overview' });
      const wrapper = region.parentElement as HTMLElement;
      // minCenterX = 48 (rail) + 20 (padding) + 192 (width/2) = 260
      expect(wrapper.style.transform).toContain('260px');

      rerender(
        <EventPopup map={westernMap} popupInsets={{ left: 384, right: 0 }} />,
      );
      // minCenterX = 384 (open chat) + 20 (padding) + 192 (width/2) = 596
      expect(wrapper.style.transform).toContain('596px');
    } finally {
      Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        value: originalWidth,
      });
      if (originalOffsetWidth) {
        Object.defineProperty(
          HTMLElement.prototype,
          'offsetWidth',
          originalOffsetWidth,
        );
      }
      if (originalOffsetHeight) {
        Object.defineProperty(
          HTMLElement.prototype,
          'offsetHeight',
          originalOffsetHeight,
        );
      }
    }
  });
});
