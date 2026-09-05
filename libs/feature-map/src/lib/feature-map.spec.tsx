import { render } from '@testing-library/react';

import HermesFeatureMap from './feature-map';

describe('HermesFeatureMap', () => {
  it('should render successfully', () => {
    const { baseElement } = render(<HermesFeatureMap />);
    expect(baseElement).toBeTruthy();
  });
});
