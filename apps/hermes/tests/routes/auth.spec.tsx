import { test, expect, vi } from 'vitest';
import { createRoutesStub } from 'react-router';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Auth from '../../app/routes/auth';

vi.mock('@clerk/react-router', () => ({
  HandleSSOCallback: () => <div data-testid="sso-callback">SSO_CALLBACK</div>,
}));

vi.mock('gsap', () => ({
  default: {
    fromTo: vi.fn(),
    set: vi.fn(),
    to: vi.fn(),
    killTweensOf: vi.fn(),
  },
}));

describe('Auth Progressive Route', () => {
  const ReactRouterStub = createRoutesStub([
    {
      path: '/auth',
      Component: Auth,
    },
  ]);

  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  test('renders auth route with email input, action button, and OAuth providers', () => {
    render(<ReactRouterStub initialEntries={['/auth']} />);

    expect(screen.getByText('Welcome to Hermes')).toBeTruthy();
    expect(screen.getByLabelText(/Email/i)).toBeTruthy();

    const continueBtn = screen.getByRole('button', { name: /^CONTINUE$/i });
    expect(continueBtn).toBeTruthy();

    expect(screen.getByText('OR CONTINUE WITH')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Continue with Google/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Continue with Facebook/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Continue with X/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Continue with Microsoft/i })).toBeTruthy();

    const patternAside = screen.getByLabelText('Geometric pattern panel');
    expect(patternAside).toBeTruthy();
  });

  test('validates invalid email format and displays error', async () => {
    render(<ReactRouterStub initialEntries={['/auth']} />);

    const emailInput = screen.getByLabelText(/Email/i);
    const continueBtn = screen.getByRole('button', { name: /^CONTINUE$/i });

    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.click(continueBtn);

    expect(screen.getByText(/Please enter a valid email address/i)).toBeTruthy();
  });

  test('progresses to OTP verification on valid email submission', async () => {
    render(<ReactRouterStub initialEntries={['/auth']} />);

    const emailInput = screen.getByLabelText(/Email/i);
    const continueBtn = screen.getByRole('button', { name: /^CONTINUE$/i });

    fireEvent.change(emailInput, { target: { value: 'operator@hermes.intel' } });
    fireEvent.click(continueBtn);

    await waitFor(
      () => {
        expect(screen.getByText('Check your inbox')).toBeTruthy();
      },
      { timeout: 3000 }
    );

    expect(screen.getByText('operator@hermes.intel')).toBeTruthy();
    expect(screen.getByLabelText('Digit 1 of 6')).toBeTruthy();
    expect(screen.getByRole('button', { name: /VERIFY & CONTINUE/i })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Use password instead/i })).toBeNull();
  });

  test('renders setup step and locks page scroll', async () => {
    window.sessionStorage.setItem('hermes_auth_email', 'operator@hermes.intel');
    window.sessionStorage.setItem('hermes_onboarding_token', 'temp_token_123');

    render(<ReactRouterStub initialEntries={['/auth?mode=setup']} />);

    await waitFor(() => {
      expect(screen.getByText('Complete your profile')).toBeTruthy();
    });

    expect(screen.getByLabelText(/Full Name/i)).toBeTruthy();
    expect(screen.getByLabelText(/^Password/i)).toBeTruthy();
    expect(screen.getByLabelText(/Confirm Password/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /COMPLETE SETUP/i })).toBeTruthy();
    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');
  });

  test('renders password fallback mode directly when state exists', async () => {
    window.sessionStorage.setItem('hermes_auth_email', 'operator@hermes.intel');

    render(<ReactRouterStub initialEntries={['/auth?mode=password']} />);

    await waitFor(() => {
      expect(screen.getByText('Enter your password')).toBeTruthy();
    });

    expect(screen.getByLabelText(/Password/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Back to 6-digit OTP verification/i })).toBeTruthy();
  });
});
