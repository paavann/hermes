import { createRoutesStub } from 'react-router';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import MapRoute from '../../app/routes/map';

vi.mock('@hermes/map', () => ({
  MapView: () => <div data-testid="map-view" />,
  MapConfigProvider: ({ children }: { children: React.ReactNode }) => children,
}));

test('renders map route with tactical hud and map view', async () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/map',
      Component: MapRoute,
    },
  ]);

  render(<ReactRouterStub initialEntries={['/map']} />);

  await waitFor(() => {
    expect(screen.getByTestId('map-view')).toBeTruthy();
  });
  expect(screen.getByText(/SYS\.TIME/)).toBeTruthy();
});
