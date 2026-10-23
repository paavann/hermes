import { test, expect, vi, beforeEach, describe } from 'vitest';
import { createRoutesStub } from 'react-router';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Auth from '../../app/routes/auth';

const mockSignIn = {
  create: vi.fn(),
  attemptFirstFactor: vi.fn(),
  prepareFirstFactor: vi.fn(),
  authenticateWithRedirect: vi.fn(),
  supportedFirstFactors: [
    { strategy: 'password' },
    { strategy: 'email_code', emailAddressId: 'email_123' },
  ],
  identifier: '',
};

const mockSignUp = {
  create: vi.fn(),
  prepareEmailAddressVerification: vi.fn(),
  attemptEmailAddressVerification: vi.fn(),
  update: vi.fn(),
  emailAddress: '',
  verifications: { emailAddress: { status: 'unverified' } },
};

const mockSetActive = vi.fn();

vi.mock('@clerk/react-router', () => ({
  useSignIn: () => ({
    isLoaded: true,
    signIn: mockSignIn,
    setActive: mockSetActive,
  }),
  useSignUp: () => ({
    isLoaded: true,
    signUp: mockSignUp,
    setActive: mockSetActive,
  }),
  useClerk: () => ({
    loaded: true,
    client: {
      signIn: mockSignIn,
      signUp: mockSignUp,
    },
    setActive: mockSetActive,
  }),
  HandleSSOCallback: () => <div data-testid="sso-callback">SSO_CALLBACK</div>,
}));

vi.mock('@clerk/react-router/legacy', () => ({
  useSignIn: () => ({
    isLoaded: true,
    signIn: mockSignIn,
    setActive: mockSetActive,
  }),
  useSignUp: () => ({
    isLoaded: true,
    signUp: mockSignUp,
    setActive: mockSetActive,
  }),
}));

vi.mock('@clerk/react-router/server', () => ({
  getAuth: vi.fn().mockResolvedValue({ userId: null, isAuthenticated: false }),
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
    {
      path: '/map',
      Component: () => <div data-testid="map-destination">MAP CONSOLE</div>,
    },
  ]);

  beforeEach(() => {
    vi.clearAllMocks();
    mockSignIn.identifier = '';
    mockSignUp.emailAddress = '';
  });

  test('renders auth route with email input, action button, and OAuth providers', () => {
    render(<ReactRouterStub initialEntries={['/auth']} />);

    expect(screen.getByText(/Welcome to Hermes/i)).toBeTruthy();
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
  }, 15000);

  test('validates invalid email format and displays error', async () => {
    render(<ReactRouterStub initialEntries={['/auth']} />);

    const emailInput = screen.getByLabelText(/Email/i);
    const continueBtn = screen.getByRole('button', { name: /^CONTINUE$/i });

    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.click(continueBtn);

    expect(screen.getByText(/Please enter a valid email address/i)).toBeTruthy();
    expect(mockSignIn.create).not.toHaveBeenCalled();
  }, 15000);

  test('existing user: progresses to login mode and reveals password field right below email', async () => {
    mockSignIn.create.mockResolvedValueOnce({
      status: 'needs_first_factor',
      supportedFirstFactors: [{ strategy: 'password' }],
    });

    render(<ReactRouterStub initialEntries={['/auth']} />);

    const emailInput = screen.getByLabelText(/Email/i);
    const continueBtn = screen.getByRole('button', { name: /^CONTINUE$/i });

    fireEvent.change(emailInput, { target: { value: 'existing@hermes.intel' } });
    fireEvent.click(continueBtn);

    await waitFor(
      () => {
        expect(mockSignIn.create).toHaveBeenCalledWith({ identifier: 'existing@hermes.intel' });
        expect(screen.getByText(/Welcome Back!/i)).toBeTruthy();
      },
      { timeout: 5000 }
    );

    // Password field is revealed
    const passwordInput = screen.getByLabelText(/^Password/i);
    expect(passwordInput).toBeTruthy();
    expect(screen.getByRole('button', { name: /^SIGN IN$/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /\[Change\]/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Sign in with OTP/i })).toBeTruthy();
  }, 15000);

  test('existing user: submits password in login mode and activates session', async () => {
    mockSignIn.identifier = 'existing@hermes.intel';
    mockSignIn.attemptFirstFactor.mockResolvedValueOnce({
      status: 'complete',
      createdSessionId: 'sess_abc123',
    });

    render(<ReactRouterStub initialEntries={['/auth?mode=login']} />);

    const emailInput = screen.getByLabelText(/Email/i) as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: 'existing@hermes.intel' } });

    const passwordInput = screen.getByLabelText(/^Password/i);
    fireEvent.change(passwordInput, { target: { value: 'OperatorSecret123!' } });

    const signInBtn = screen.getByRole('button', { name: /^SIGN IN$/i });
    fireEvent.click(signInBtn);

    await waitFor(
      () => {
        expect(mockSignIn.attemptFirstFactor).toHaveBeenCalledWith({
          strategy: 'password',
          password: 'OperatorSecret123!',
        });
        expect(mockSetActive).toHaveBeenCalledWith({ session: 'sess_abc123' });
      },
      { timeout: 5000 }
    );
  }, 15000);

  test('new user: converts to OTP verification when identifier is not found', async () => {
    mockSignIn.create.mockRejectedValueOnce({
      errors: [{ code: 'form_identifier_not_found', message: 'Not found' }],
    });
    mockSignUp.create.mockResolvedValueOnce({});
    mockSignUp.prepareEmailAddressVerification.mockResolvedValueOnce({});

    render(<ReactRouterStub initialEntries={['/auth']} />);

    const emailInput = screen.getByLabelText(/Email/i);
    const continueBtn = screen.getByRole('button', { name: /^CONTINUE$/i });

    fireEvent.change(emailInput, { target: { value: 'newoperator@hermes.intel' } });
    fireEvent.click(continueBtn);

    await waitFor(
      () => {
        expect(mockSignIn.create).toHaveBeenCalledWith({ identifier: 'newoperator@hermes.intel' });
        expect(mockSignUp.create).toHaveBeenCalledWith({ emailAddress: 'newoperator@hermes.intel' });
        expect(mockSignUp.prepareEmailAddressVerification).toHaveBeenCalledWith({
          strategy: 'email_code',
        });
        expect(screen.getByText('Check your inbox')).toBeTruthy();
      },
      { timeout: 5000 }
    );

    expect(screen.getByText('newoperator@hermes.intel')).toBeTruthy();
    expect(screen.getByLabelText('Digit 1 of 6')).toBeTruthy();
  }, 15000);

  test('new user: verifies OTP and transitions to setup mode', async () => {
    mockSignUp.emailAddress = 'newoperator@hermes.intel';
    mockSignUp.attemptEmailAddressVerification.mockResolvedValueOnce({
      verifications: { emailAddress: { status: 'verified' } },
    });

    render(<ReactRouterStub initialEntries={['/auth?mode=otp&flow=sign-up']} />);

    const digit1 = screen.getByLabelText('Digit 1 of 6');
    fireEvent.change(digit1, { target: { value: '123456' } });

    const verifyBtn = screen.getByRole('button', { name: /VERIFY & CONTINUE/i });
    fireEvent.click(verifyBtn);

    await waitFor(
      () => {
        expect(mockSignUp.attemptEmailAddressVerification).toHaveBeenCalledWith({
          code: '123456',
        });
      },
      { timeout: 5000 }
    );
  }, 15000);

  test('new user: completes setup with name and password and activates session', async () => {
    mockSignUp.emailAddress = 'newoperator@hermes.intel';
    mockSignUp.update.mockResolvedValueOnce({
      status: 'complete',
      createdSessionId: 'sess_new_456',
    });

    render(<ReactRouterStub initialEntries={['/auth?mode=setup']} />);

    const nameInput = screen.getByLabelText(/Full Name/i);
    const passwordInput = screen.getByLabelText(/^Password/i);
    const confirmInput = screen.getByLabelText(/Confirm Password/i);

    fireEvent.change(nameInput, { target: { value: 'Elena Rostova' } });
    fireEvent.change(passwordInput, { target: { value: 'Tactical2026!' } });
    fireEvent.change(confirmInput, { target: { value: 'Tactical2026!' } });

    const setupBtn = screen.getByRole('button', { name: /COMPLETE SETUP/i });
    fireEvent.click(setupBtn);

    await waitFor(
      () => {
        expect(mockSignUp.update).toHaveBeenCalledWith({
          firstName: 'Elena',
          lastName: 'Rostova',
          password: 'Tactical2026!',
        });
        expect(mockSetActive).toHaveBeenCalledWith({ session: 'sess_new_456' });
      },
      { timeout: 5000 }
    );
  }, 15000);

  test('triggers OAuth redirect when a social provider button is clicked', async () => {
    mockSignIn.authenticateWithRedirect.mockResolvedValueOnce({});

    render(<ReactRouterStub initialEntries={['/auth']} />);

    const googleBtn = screen.getByRole('button', { name: /Continue with Google/i });
    fireEvent.click(googleBtn);

    await waitFor(
      () => {
        expect(mockSignIn.authenticateWithRedirect).toHaveBeenCalledWith({
          strategy: 'oauth_google',
          redirectUrl: '/auth/sso-callback',
          redirectUrlComplete: '/map',
          continueSignUp: true,
        });
      },
      { timeout: 5000 }
    );
  }, 15000);
});
