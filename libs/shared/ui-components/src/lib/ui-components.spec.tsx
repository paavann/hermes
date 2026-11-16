import { act, fireEvent, render, screen } from '@testing-library/react';
import { createRoutesStub } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { BootSequence } from './BootSequence';
import { CornerReticle } from './CornerReticle';
import { HermesWordmark } from './HermesWordmark';
import { LiveClock } from './LiveClock';
import { OAuthButtonGroup } from './OAuthButtonGroup';
import { RollButton } from './RollButton';
import { TacticalActionBtn } from './TacticalActionBtn';

vi.mock('gsap', () => ({
  default: {
    fromTo: vi.fn(),
    killTweensOf: vi.fn(),
    registerPlugin: vi.fn(),
    set: vi.fn(),
    to: vi.fn(),
  },
}));

describe('CornerReticle', () => {
  it('renders four decorative brackets with the default tone and size', () => {
    const { container } = render(<CornerReticle />);

    const root = container.firstElementChild as HTMLElement;
    expect(root.getAttribute('aria-hidden')).toBe('true');
    expect(root.className).toContain('pointer-events-none');

    const brackets = container.querySelectorAll('span');
    expect(brackets).toHaveLength(4);
    brackets.forEach((bracket) => {
      expect(bracket.className).toContain('h-4');
      expect(bracket.className).toContain('w-4');
      expect(bracket.className).toContain('border-neon-blue/80');
    });
  });

  it('applies the requested tone, size, and layout class', () => {
    const { container } = render(
      <CornerReticle tone="bone" size="lg" className="inset-3" />,
    );

    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toContain('inset-3');

    const brackets = container.querySelectorAll('span');
    brackets.forEach((bracket) => {
      expect(bracket.className).toContain('h-6');
      expect(bracket.className).toContain('w-6');
      expect(bracket.className).toContain('border-bone/40');
    });
  });
});

describe('LiveClock', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-16T12:34:56Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the current UTC time and advances every second', () => {
    render(<LiveClock />);

    expect(screen.getByText('12:34:56 UTC')).toBeTruthy();

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText('12:34:57 UTC')).toBeTruthy();
  });

  it('merges a caller-supplied class and clears its interval on unmount', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const { unmount } = render(<LiveClock className="bottom-8" />);

    const clock = screen.getByText('12:34:56 UTC');
    expect(clock.parentElement?.className).toContain('bottom-8');

    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});

describe('HermesWordmark', () => {
  it('exposes an accessible image role and forwards svg props', () => {
    render(<HermesWordmark data-testid="wordmark" className="text-bone" />);

    const wordmark = screen.getByRole('img', { name: 'Hermes' });
    expect(wordmark.getAttribute('data-testid')).toBe('wordmark');
    expect(wordmark.getAttribute('viewBox')).toBe('45 96 1370 284');
    expect(wordmark.getAttribute('class')).toContain('text-bone');
  });
});

describe('OAuthButtonGroup', () => {
  it('renders every provider and reports the selected id', () => {
    const onSelect = vi.fn();
    render(<OAuthButtonGroup onSelect={onSelect} />);

    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeTruthy();
    expect(
      screen.getByRole('button', { name: 'Continue with Facebook' }),
    ).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Continue with X' })).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Facebook' }));
    expect(onSelect).toHaveBeenCalledWith('facebook');
  });

  it('shows a connecting state for the active provider and disables all buttons', () => {
    render(
      <OAuthButtonGroup
        activeProvider="x"
        onSelect={vi.fn()}
        disabled
      />,
    );

    expect(screen.getByText('CONNECTING...')).toBeTruthy();
    screen.getAllByRole('button').forEach((button) => {
      expect((button as HTMLButtonElement).disabled).toBe(true);
    });

    const xButton = screen.getByRole('button', { name: 'Continue with X' });
    expect(xButton.className).toContain('border-neon-blue');
  });
});

describe('RollButton', () => {
  const renderWithRouter = (ui: React.ReactElement) => {
    const Stub = createRoutesStub([
      { path: '/', Component: () => ui },
      { path: '/map', Component: () => <div>map</div> },
    ]);
    return render(<Stub initialEntries={['/']} />);
  };

  it('renders both rolling labels and links to the requested route', () => {
    renderWithRouter(<RollButton to="/map" />);

    expect(screen.getAllByText('LAUNCH MAP')).toHaveLength(1);
    expect(screen.getByText('LAUNCH MAP ↗')).toBeTruthy();

    const link = screen.getByRole('link', {
      name: 'Launch the intelligence map',
    });
    expect(link.getAttribute('href')).toBe('/map');
  });

  it('renders an anchor for external hrefs and invokes onClick', () => {
    const onClick = vi.fn();
    render(
      <RollButton
        href="https://example.com"
        label="OPEN"
        hoverLabel="OPEN ↗"
        ariaLabel="Open example"
        onClick={onClick}
      />,
    );

    const link = screen.getByRole('link', { name: 'Open example' });
    expect(link.getAttribute('href')).toBe('https://example.com');
    expect(link.getAttribute('target')).toBeNull();

    fireEvent.click(link);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('falls back to a button when no destination is supplied', () => {
    const onClick = vi.fn();
    render(<RollButton label="RUN" ariaLabel="Run task" onClick={onClick} />);

    const button = screen.getByRole('button', { name: 'Run task' });
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe('TacticalActionBtn', () => {
  it('renders the label and submits by default', () => {
    render(<TacticalActionBtn label="SEND" />);

    const button = screen.getByRole('button', { name: 'SEND' });
    expect(button.getAttribute('type')).toBe('submit');
    expect((button as HTMLButtonElement).disabled).toBe(false);
  });

  it('swaps in the loading label and disables while submitting', () => {
    const onClick = vi.fn();
    render(
      <TacticalActionBtn
        label="SEND"
        loadingLabel="SENDING..."
        isSubmitting
        onClick={onClick}
      />,
    );

    const button = screen.getByRole('button', { name: 'SENDING...' });
    expect((button as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('supports an explicit aria label and slide variant', () => {
    const onClick = vi.fn();
    render(
      <TacticalActionBtn
        label="SEND"
        ariaLabel="Send message"
        variant="slide"
        type="button"
        onClick={onClick}
      />,
    );

    const button = screen.getByRole('button', { name: 'Send message' });
    expect(button.getAttribute('type')).toBe('button');
    expect(button.className).toContain('py-4');

    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe('BootSequence', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the terminal cursor and starts scrambling after one second', () => {
    const { container } = render(<BootSequence onComplete={vi.fn()} />);

    expect(container.textContent).toContain('_');

    act(() => {
      vi.advanceTimersByTime(1080);
    });

    expect((container.textContent ?? '').length).toBeGreaterThan(1);
  });

  it('clears its timers on unmount', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout');
    const { unmount } = render(<BootSequence onComplete={vi.fn()} />);

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    expect(clearTimeoutSpy).toHaveBeenCalled();
  });
});
