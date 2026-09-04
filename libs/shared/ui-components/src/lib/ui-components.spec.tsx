import { render } from '@testing-library/react';

import HermesUiComponents from './ui-components';

describe('HermesUiComponents', () => {
  it('should render successfully', () => {
    const { baseElement } = render(<HermesUiComponents />);
    expect(baseElement).toBeTruthy();
  });
});
