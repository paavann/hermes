import { createRoutesStub } from 'react-router';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Landing from '../../app/routes/landing';

describe('Landing Page Route', () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/',
      Component: Landing,
    },
  ]);

  it('renders landing hero, sections, access clearance form, and brutalist footer', () => {
    render(<ReactRouterStub />);

    // Header & Navigation
    expect(screen.getByText('Hermes Intelligence')).toBeTruthy();
    expect(screen.getByText('Global event observability for')).toBeTruthy();

    // The Problem
    expect(screen.getAllByText('The Problem').length).toBeGreaterThan(0);

    // Capabilities
    expect(screen.getAllByText('Capabilities').length).toBeGreaterThan(0);

    // Access Section
    expect(screen.getAllByText('Access').length).toBeGreaterThan(0);
    expect(screen.getByText(/Request early dispatch/)).toBeTruthy();
    expect(screen.getByLabelText(/FULL NAME/)).toBeTruthy();
    expect(screen.getByLabelText(/DISPATCH ADDRESS/)).toBeTruthy();

    // Footer
    expect(screen.getByText(/HERMES GEOINT INC/)).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Hermes' })).toBeTruthy();
  }, 15000);

  it('handles access form dispatch submission', async () => {
    render(<ReactRouterStub />);

    const nameInput = screen.getByLabelText(/FULL NAME/);
    const emailInput = screen.getByLabelText(/DISPATCH ADDRESS/);
    const submitBtn = screen.getByRole('button', { name: /TRANSMIT DISPATCH REQUEST/i });

    fireEvent.change(nameInput, { target: { value: 'Agent Test' } });
    fireEvent.change(emailInput, { target: { value: 'agent@hermes.intel' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/200 OK \/\/ DISPATCH LOGGED/)).toBeTruthy();
    });

    expect(screen.getByText(/agent@hermes.intel/)).toBeTruthy();
  }, 15000);
});
