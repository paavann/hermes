import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { MapConfig } from './config-context';
import { MapConfigProvider, useMapConfig } from './config-context';

const CONFIG: MapConfig = {
  baseUrl: 'https://api.hermes.test',
  apiVer: 'v1',
  mapboxToken: 'pk.test-token',
};

function ConfigProbe(): React.JSX.Element {
  const config = useMapConfig();
  return (
    <span data-testid="config">
      {config.baseUrl}|{config.apiVer}|{config.mapboxToken}
    </span>
  );
}

describe('MapConfigProvider', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('supplies the injected configuration to descendants', () => {
    render(
      <MapConfigProvider config={CONFIG}>
        <ConfigProbe />
      </MapConfigProvider>,
    );

    expect(screen.getByTestId('config').textContent).toBe(
      'https://api.hermes.test|v1|pk.test-token',
    );
  });

  it('lets a nested provider override the outer configuration', () => {
    render(
      <MapConfigProvider config={CONFIG}>
        <MapConfigProvider config={{ ...CONFIG, apiVer: 'v2' }}>
          <ConfigProbe />
        </MapConfigProvider>
      </MapConfigProvider>,
    );

    expect(screen.getByTestId('config').textContent).toContain('|v2|');
  });

  it('throws when the hook is used outside a provider', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    expect(() => render(<ConfigProbe />)).toThrow(
      'useMapConfig must be used within a MapConfigProvider',
    );
  });
});
