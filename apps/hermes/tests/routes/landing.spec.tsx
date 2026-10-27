import { createRoutesStub } from 'react-router';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import Landing from '../../app/routes/landing';

let mockAuthState: 'signed-out' | 'signed-in' = 'signed-out';

vi.mock('@clerk/react-router', () => ({
  Show: ({ when, children }: { when: string; children: React.ReactNode }) =>
    when === mockAuthState ? children : null,
  SignOutButton: ({ children }: { children: React.ReactNode }) => children,
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
  SignUpButton: ({ children }: { children: React.ReactNode }) => children,
}));

describe('Landing Page Route', () => {
  beforeEach(() => {
    mockAuthState = 'signed-out';
  });

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

  it('renders LOGIN link pointing to /auth and no LOGOUT when signed out', () => {
    mockAuthState = 'signed-out';
    render(<ReactRouterStub />);

    const loginLinks = screen.getAllByRole('link', { name: /^LOGIN$/i });
    expect(loginLinks.length).toBeGreaterThan(0);
    expect(loginLinks[0].getAttribute('href')).toBe('/auth');

    expect(screen.queryByRole('button', { name: /^LOGOUT$/i })).toBeNull();
    expect(screen.queryByText(/OPERATOR PROFILE/i)).toBeNull();
  }, 15000);

  it('renders LOGOUT button and no LOGIN link when signed in', () => {
    mockAuthState = 'signed-in';
    render(<ReactRouterStub />);

    const logoutButtons = screen.getAllByRole('button', { name: /^LOGOUT$/i });
    expect(logoutButtons.length).toBeGreaterThan(0);

    expect(screen.queryByRole('link', { name: /^LOGIN$/i })).toBeNull();
    expect(screen.queryByText(/OPERATOR PROFILE/i)).toBeNull();
  }, 15000);

  it('handles contact form transmission submission', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      new Response(JSON.stringify({ next: 'https://formspree.io/thanks' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

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
        expect(screen.getByText(/MESSAGE RECEIVED/)).toBeTruthy();
      },
      { timeout: 4000 }
    );

    expect(screen.getByText(/agent@hermes.intel/)).toBeTruthy();
  }, 15000);
});
