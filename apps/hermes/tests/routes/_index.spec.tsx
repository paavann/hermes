import { createRoutesStub } from 'react-router';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import App from '../../app/app';

vi.mock('@hermes/feature-map', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hermes/feature-map')>();
  return {
    ...actual,
    MapView: () => <div data-testid="map-view" />,
  };
});

test('renders app shell with tactical hud and map view', async () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/',
      Component: App,
    },
  ]);

  render(<ReactRouterStub />);

  await waitFor(() => {
    expect(screen.getByTestId('map-view')).toBeTruthy();
  });
  expect(screen.getByText(/SYS\.TIME/)).toBeTruthy();
});

