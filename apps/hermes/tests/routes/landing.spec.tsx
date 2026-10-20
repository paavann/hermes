import { createRoutesStub } from 'react-router';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import Landing from '../../app/routes/landing';

vi.mock('@clerk/react-router', () => ({
  Show: ({ when, children }: { when: string; children: React.ReactNode }) =>
    when === 'signed-out' ? children : null,
  UserButton: () => <div data-testid="user-button">USER_BUTTON</div>,
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
  SignUpButton: ({ children }: { children: React.ReactNode }) => children,
}));

describe('Landing Page Route', () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/',
      Component: Landing,
    },
  ]);

  it('renders landing hero, sections, contact form, and brutalist footer', () => {
    render(<ReactRouterStub />);

    // Header & Navigation
    expect(screen.getByText('Hermes Intelligence')).toBeTruthy();
    expect(screen.getByText('Global event observability for')).toBeTruthy();

    // The Problem
    expect(screen.getAllByText('The Problem').length).toBeGreaterThan(0);

    // Capabilities
    expect(screen.getAllByText('Capabilities').length).toBeGreaterThan(0);

    // Contact Section
    expect(screen.getAllByText('Contact').length).toBeGreaterThan(0);
    expect(screen.getByText(/Have questions or feedback\?/)).toBeTruthy();
    expect(screen.getByLabelText(/NAME \*/)).toBeTruthy();
    expect(screen.getByLabelText(/EMAIL ADDRESS \*/)).toBeTruthy();

    // Footer
    expect(screen.getByText(/HERMES GEOINT INC/)).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Hermes' })).toBeTruthy();
  }, 15000);

  it('handles contact form transmission submission', async () => {
    render(<ReactRouterStub />);

    const nameInput = screen.getByLabelText(/NAME \*/);
    const emailInput = screen.getByLabelText(/EMAIL ADDRESS \*/);
    const messageInput = screen.getByLabelText(/MESSAGE \*/);
    const submitBtn = screen.getByRole('button', { name: /Send message/i });

    fireEvent.change(nameInput, { target: { value: 'Agent Test' } });
    fireEvent.change(emailInput, { target: { value: 'agent@hermes.intel' } });
    fireEvent.change(messageInput, { target: { value: 'Testing contact submission' } });
    fireEvent.click(submitBtn);

    await waitFor(
      () => {
        expect(screen.getByText(/200 OK \/\/ MESSAGE RECEIVED/)).toBeTruthy();
      },
      { timeout: 4000 }
    );

    expect(screen.getByText(/agent@hermes.intel/)).toBeTruthy();
  }, 15000);
});
