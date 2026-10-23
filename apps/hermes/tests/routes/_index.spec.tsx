import { createRoutesStub } from 'react-router';
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import MapRoute, { loader as mapLoader, HydrateFallback } from '../../app/routes/map';

const mockGetAuth = vi.fn();

vi.mock('@clerk/react-router/server', () => ({
  getAuth: (...args: unknown[]) => mockGetAuth(...args),
}));

vi.mock('@hermes/map', () => ({
  MapView: () => <div data-testid="map-view" />,
  MapConfigProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('Map Route', () => {
  beforeEach(() => {
    mockGetAuth.mockReset();
  });

  const ReactRouterStub = createRoutesStub([
    {
      path: '/map',
      Component: MapRoute,
      loader: mapLoader,
      HydrateFallback,
    },
  ]);

  it('renders map route with tactical hud and map view for authenticated users', async () => {
    mockGetAuth.mockResolvedValueOnce({ userId: 'user_operator_123', isAuthenticated: true });

    render(<ReactRouterStub initialEntries={['/map']} />);

    await waitFor(
      () => {
        expect(screen.getByTestId('map-view')).toBeTruthy();
        expect(screen.getByText(/SYS\.TIME/)).toBeTruthy();
      },
      { timeout: 5000 }
    );
  }, 15000);

  it('renders map route without redirection for unauthenticated visitors', async () => {
    mockGetAuth.mockResolvedValueOnce({ userId: null, isAuthenticated: false });

    render(<ReactRouterStub initialEntries={['/map']} />);

    await waitFor(
      () => {
        expect(screen.getByTestId('map-view')).toBeTruthy();
        expect(screen.getByText(/SYS\.TIME/)).toBeTruthy();
      },
      { timeout: 5000 }
    );
  }, 15000);
});
