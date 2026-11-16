// @vitest-environment node
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import MapRoute, {
  HydrateFallback,
  MapLoadingFallback,
} from '../../app/routes/map';

describe('map route SSR', () => {
  it('renders the loading fallbacks without evaluating browser map code', () => {
    expect(renderToStaticMarkup(<MapLoadingFallback />)).toContain(
      'LOADING LIVE MAP',
    );
    expect(renderToStaticMarkup(<HydrateFallback />)).toContain(
      'LOADING LIVE MAP',
    );
    expect(typeof MapRoute).toBe('function');
  });
});
