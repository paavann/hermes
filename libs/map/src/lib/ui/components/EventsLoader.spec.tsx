import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { EventsLoader } from './EventsLoader';

describe('EventsLoader', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders a solid sync badge with no glow or pulse animation', () => {
    render(<EventsLoader />);

    const badge = screen.getByRole('status');
    expect(badge).toBeTruthy();
    expect(badge.className).toContain('bg-black');
    expect(badge.className).toContain('text-neon-blue');
    expect(badge.className).not.toContain('shadow');
    expect(badge.className).not.toContain('backdrop-blur');
    expect(badge.className).not.toContain('animate-pulse');
    expect(badge.textContent).toContain('SYNCING');
  });

  it('cycles three dots disappearing sequentially from left to right', () => {
    const { container } = render(<EventsLoader />);

    // Step 0: All 3 dots visible (opacity-100)
    let dots = container.querySelectorAll('span[aria-hidden="true"] > span');
    expect(dots).toHaveLength(3);
    expect(dots[0].className).toContain('opacity-100');
    expect(dots[1].className).toContain('opacity-100');
    expect(dots[2].className).toContain('opacity-100');

    // Step 1 (+300ms): 1st dot disappears (leftmost)
    act(() => {
      vi.advanceTimersByTime(300);
    });
    dots = container.querySelectorAll('span[aria-hidden="true"] > span');
    expect(dots[0].className).toContain('opacity-0');
    expect(dots[1].className).toContain('opacity-100');
    expect(dots[2].className).toContain('opacity-100');

    // Step 2 (+300ms): 2nd dot disappears (middle)
    act(() => {
      vi.advanceTimersByTime(300);
    });
    dots = container.querySelectorAll('span[aria-hidden="true"] > span');
    expect(dots[0].className).toContain('opacity-0');
    expect(dots[1].className).toContain('opacity-0');
    expect(dots[2].className).toContain('opacity-100');

    // Step 3 (+300ms): 3rd dot disappears (all gone)
    act(() => {
      vi.advanceTimersByTime(300);
    });
    dots = container.querySelectorAll('span[aria-hidden="true"] > span');
    expect(dots[0].className).toContain('opacity-0');
    expect(dots[1].className).toContain('opacity-0');
    expect(dots[2].className).toContain('opacity-0');

    // Step 4 (+300ms): Reset back to all 3 dots visible
    act(() => {
      vi.advanceTimersByTime(300);
    });
    dots = container.querySelectorAll('span[aria-hidden="true"] > span');
    expect(dots[0].className).toContain('opacity-100');
    expect(dots[1].className).toContain('opacity-100');
    expect(dots[2].className).toContain('opacity-100');
  });

  it('cleans up interval timer on unmount', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const { unmount } = render(<EventsLoader />);

    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});
