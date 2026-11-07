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
    trending_score: 95,
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
});
