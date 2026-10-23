import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams, useLocation, useParams } from 'react-router';
import { useClerk } from '@clerk/react-router';
import { useSignIn, useSignUp } from '@clerk/react-router/legacy';
import type { OAuthStrategy, EmailCodeFactor, SignInFirstFactor } from '@clerk/shared/types';
import gsap from 'gsap';
import type { OAuthProviderId } from '@hermes/ui-components';
import type { AuthMode, AuthStatus } from './types';

export interface UseAuthWorkflowReturn {
  readonly isSsoCallback: boolean;
  readonly currentMode: AuthMode;
  readonly modeContainerRef: React.RefObject<HTMLDivElement | null>;
  readonly email: string;
  readonly otpDigits: readonly string[];
  readonly otpInputRefs: React.RefObject<(HTMLInputElement | null)[]>;
  readonly resendCooldown: number;
  readonly fullName: string;
  readonly password: string;
  readonly confirmPassword: string;
  readonly status: AuthStatus;
  readonly activeOAuth: OAuthProviderId | null;
  readonly errorMsg: string | null;
  readonly isBusy: boolean;
  readonly setEmail: (email: string) => void;
  readonly setFullName: (name: string) => void;
  readonly setPassword: (password: string) => void;
  readonly setConfirmPassword: (password: string) => void;
  readonly handleEmailSubmit: (e: React.FormEvent<HTMLFormElement>) => Promise<void>;
  readonly handlePasswordSubmit: (e: React.FormEvent<HTMLFormElement>) => Promise<void>;
  readonly handleOAuthClick: (providerId: OAuthProviderId) => Promise<void>;
  readonly handleOtpChange: (index: number, rawValue: string) => void;
  readonly handleOtpKeyDown: (index: number, e: React.KeyboardEvent<HTMLInputElement>) => void;
  readonly handleOtpPaste: (e: React.ClipboardEvent<HTMLInputElement>) => void;
  readonly handleOtpSubmit: (e: React.FormEvent<HTMLFormElement>) => Promise<void>;
  readonly handleResendOtp: () => Promise<void>;
  readonly handleSetupSubmit: (e: React.FormEvent<HTMLFormElement>) => Promise<void>;
  readonly handleChangeEmail: () => void;
  readonly handleSwitchToOtpFromLogin: () => Promise<void>;
}

export function extractClerkError(err: unknown): string {
  if (typeof err === 'object' && err !== null && 'errors' in err) {
    const clerkErr = err as {
      errors: Array<{ message?: string; longMessage?: string; code?: string }>;
    };
    const first = clerkErr.errors?.[0];
    if (!first) return 'An error occurred during authentication.';
    if (first.code === 'form_password_pwned') {
      return 'Password was compromised in an external data breach. Select a stronger password.';
    }
    if (first.code === 'form_code_incorrect') {
      return 'Verification code is invalid. Check your inbox and retry.';
    }
    if (first.code === 'form_password_incorrect') {
      return 'Incorrect password. Please verify and retry.';
    }
    if (first.code === 'form_identifier_not_found') {
      return 'Operator account not found.';
    }
    if (first.code === 'form_param_format_invalid') {
      return 'Invalid email address format.';
    }
    return first.longMessage || first.message || 'Authentication request failed.';
  }
  if (err instanceof Error) {
    return err.message;
  }
  return 'An unexpected error occurred during authentication.';
}

const OAUTH_STRATEGY_MAP: Record<OAuthProviderId, OAuthStrategy> = {
  google: 'oauth_google',
  facebook: 'oauth_facebook',
  x: 'oauth_x',
};

export function useAuthWorkflow(): UseAuthWorkflowReturn {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const modeContainerRef = useRef<HTMLDivElement | null>(null);

  const clerk = useClerk();
  const { isLoaded: isSignInLoaded, signIn: legacySignIn, setActive: legacySetActive } = useSignIn();
  const { isLoaded: isSignUpLoaded, signUp: legacySignUp } = useSignUp();

  const isClerkLoaded = Boolean(
    clerk?.loaded ||
    (isSignInLoaded && isSignUpLoaded) ||
    (typeof window !== 'undefined' && (window as unknown as { Clerk?: { loaded?: boolean } }).Clerk?.loaded)
  );

  const signIn = legacySignIn || clerk.client?.signIn;
  const signUp = legacySignUp || clerk.client?.signUp;
  const setActive = legacySetActive || clerk.setActive;

  const isSsoCallback =
    params['*'] === 'sso-callback' ||
    location.pathname.endsWith('/sso-callback') ||
    searchParams.get('mode') === 'sso-callback';

  const rawMode = searchParams.get('mode');
  const currentMode: AuthMode =
    rawMode === 'login' || rawMode === 'otp' || rawMode === 'setup'
      ? rawMode
      : 'email';

  const flowParam = searchParams.get('flow');
  const flowType: 'sign-in' | 'sign-up' =
    flowParam === 'sign-up' || (!signIn?.identifier && Boolean(signUp?.emailAddress))
      ? 'sign-up'
      : 'sign-in';
  const [email, setEmail] = useState<string>(() => signIn?.identifier || signUp?.emailAddress || '');
  const [otpDigits, setOtpDigits] = useState<string[]>(['', '', '', '', '', '']);
  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [resendCooldown, setResendCooldown] = useState<number>(0);

  const [fullName, setFullName] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');

  const [status, setStatus] = useState<AuthStatus>('idle');
  const [activeOAuth, setActiveOAuth] = useState<OAuthProviderId | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isBusy = status === 'submitting' || !isClerkLoaded || activeOAuth !== null;

  // Protect against direct manual navigation to deep steps without prior email context
  useEffect(() => {
    if (isSsoCallback) return;

    const hasActiveContext =
      email.trim() ||
      signIn?.identifier ||
      signUp?.emailAddress;

    if ((currentMode === 'login' || currentMode === 'otp' || currentMode === 'setup') && !hasActiveContext) {
      setSearchParams({}, { replace: true });
    }
  }, [currentMode, email, signIn?.identifier, signUp?.emailAddress, setSearchParams, isSsoCallback]);

  // Visual entrance animation on step changes
  useEffect(() => {
    setErrorMsg(null);

    if (modeContainerRef.current) {
      gsap.fromTo(
        modeContainerRef.current,
        { autoAlpha: 0, y: 8 },
        { autoAlpha: 1, y: 0, duration: 0.28, ease: 'power2.out' }
      );
    }

    if (!isSsoCallback && currentMode === 'otp') {
      const timer = window.setTimeout(() => {
        otpInputRefs.current[0]?.focus();
      }, 40);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [currentMode, isSsoCallback]);

  // Resend cooldown countdown
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = window.setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendCooldown]);

  const handleEmailSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    const trimmedEmail = email.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!trimmedEmail || !emailRegex.test(trimmedEmail)) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    if (!isClerkLoaded || !signIn || !signUp) {
      return;
    }

    setErrorMsg(null);
    setStatus('submitting');

    try {
      // 1. Attempt to find existing user via signIn.create
      await signIn.create({ identifier: trimmedEmail });

      // User exists! Advance directly to login mode with revealed password field
      setStatus('idle');
      setSearchParams({ mode: 'login' });
    } catch (err: unknown) {
      const firstCode =
        typeof err === 'object' && err !== null && 'errors' in err
          ? (err as { errors: Array<{ code?: string }> }).errors?.[0]?.code
          : undefined;

      if (firstCode === 'form_identifier_not_found') {
        // User does not exist! Gracefully convert to registration via signUp
        try {
          await signUp.create({ emailAddress: trimmedEmail });
          await signUp.prepareEmailAddressVerification({ strategy: 'email_code' });

          setStatus('idle');
          setOtpDigits(['', '', '', '', '', '']);
          setResendCooldown(30);
          setSearchParams({ mode: 'otp', flow: 'sign-up' });
        } catch (signUpErr: unknown) {
          setStatus('idle');
          setErrorMsg(extractClerkError(signUpErr));
        }
      } else {
        setStatus('idle');
        setErrorMsg(extractClerkError(err));
      }
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!password.trim()) {
      setErrorMsg('Please enter your password.');
      return;
    }

    if (!isClerkLoaded || !signIn) return;

    setErrorMsg(null);
    setStatus('submitting');

    try {
      const result = await signIn.attemptFirstFactor({
        strategy: 'password',
        password,
      });

      if (result.status === 'complete') {
        if (setActive) {
          await setActive({ session: result.createdSessionId });
        }
        navigate('/map', { replace: true });
      } else {
        setStatus('idle');
        setErrorMsg('Authentication incomplete. Please check verification requirements.');
      }
    } catch (err: unknown) {
      setStatus('idle');
      setErrorMsg(extractClerkError(err));
    }
  };

  const handleSwitchToOtpFromLogin = async (): Promise<void> => {
    if (!isClerkLoaded || !signIn) return;
    setErrorMsg(null);
    setStatus('submitting');

    try {
      const isEmailCodeFactor = (factor: SignInFirstFactor): factor is EmailCodeFactor =>
        factor.strategy === 'email_code';

      const emailCodeFactor = signIn.supportedFirstFactors?.find(isEmailCodeFactor);

      if (!emailCodeFactor) {
        setStatus('idle');
        setErrorMsg('Email verification code is not configured for this account.');
        return;
      }

      await signIn.prepareFirstFactor({
        strategy: 'email_code',
        emailAddressId: emailCodeFactor.emailAddressId,
      });

      setStatus('idle');
      setOtpDigits(['', '', '', '', '', '']);
      setResendCooldown(30);
      setSearchParams({ mode: 'otp', flow: 'sign-in' });
    } catch (err: unknown) {
      setStatus('idle');
      setErrorMsg(extractClerkError(err));
    }
  };

  const handleOAuthClick = async (providerId: OAuthProviderId): Promise<void> => {
    if (isBusy || !isClerkLoaded || !signIn) return;
    setErrorMsg(null);
    setActiveOAuth(providerId);

    try {
      const strategy = OAUTH_STRATEGY_MAP[providerId];
      await signIn.authenticateWithRedirect({
        strategy,
        redirectUrl: '/auth/sso-callback',
        redirectUrlComplete: '/map',
        continueSignUp: true,
      });
    } catch (err: unknown) {
      setActiveOAuth(null);
      setErrorMsg(extractClerkError(err));
    }
  };

  const handleOtpChange = (index: number, rawValue: string): void => {
    const cleanDigits = rawValue.replace(/\D/g, '');

    if (!cleanDigits) {
      const next = [...otpDigits];
      next[index] = '';
      setOtpDigits(next);
      return;
    }

    if (cleanDigits.length > 1) {
      const next = [...otpDigits];
      for (let i = 0; i < cleanDigits.length && index + i < 6; i += 1) {
        next[index + i] = cleanDigits[i];
      }
      setOtpDigits(next);
      const nextFocusIdx = Math.min(index + cleanDigits.length, 5);
      otpInputRefs.current[nextFocusIdx]?.focus();
      return;
    }

    const next = [...otpDigits];
    next[index] = cleanDigits;
    setOtpDigits(next);

    if (index < 5) {
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>
  ): void => {
    if (e.key === 'Backspace') {
      if (otpDigits[index]) {
        const next = [...otpDigits];
        next[index] = '';
        setOtpDigits(next);
      } else if (index > 0) {
        const next = [...otpDigits];
        next[index - 1] = '';
        setOtpDigits(next);
        otpInputRefs.current[index - 1]?.focus();
      }
      e.preventDefault();
    } else if (e.key === 'ArrowLeft' && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
      e.preventDefault();
    } else if (e.key === 'ArrowRight' && index < 5) {
      otpInputRefs.current[index + 1]?.focus();
      e.preventDefault();
    }
  };

  const handleOtpPaste = (e: React.ClipboardEvent<HTMLInputElement>): void => {
    e.preventDefault();
    const pastedDigits = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pastedDigits) return;

    const next = [...otpDigits];
    for (let i = 0; i < 6; i += 1) {
      next[i] = pastedDigits[i] || '';
    }
    setOtpDigits(next);

    const focusIdx = Math.min(pastedDigits.length, 5);
    otpInputRefs.current[focusIdx]?.focus();
  };

  const handleOtpSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    const code = otpDigits.join('');
    if (code.length < 6) {
      setErrorMsg('Please enter all 6 digits of your verification code.');
      return;
    }
    if (!isClerkLoaded) return;

    setErrorMsg(null);
    setStatus('submitting');

    try {
      if (flowType === 'sign-in') {
        if (!signIn) return;
        const result = await signIn.attemptFirstFactor({
          strategy: 'email_code',
          code,
        });

        if (result.status === 'complete') {
          if (setActive) {
            await setActive({ session: result.createdSessionId });
          }
          navigate('/map', { replace: true });
        } else {
          setStatus('idle');
          setErrorMsg('Sign-in requires additional verification steps.');
        }
      } else {
        if (!signUp) return;
        const result = await signUp.attemptEmailAddressVerification({ code });

        if (result.verifications.emailAddress.status === 'verified') {
          setStatus('idle');
          setSearchParams({ mode: 'setup' }, { replace: true });
        } else {
          setStatus('idle');
          setErrorMsg('Verification code could not be confirmed.');
        }
      }
    } catch (err: unknown) {
      setStatus('idle');
      setErrorMsg(extractClerkError(err));
    }
  };

  const handleResendOtp = async (): Promise<void> => {
    if (resendCooldown > 0 || isBusy || !isClerkLoaded) return;
    setOtpDigits(['', '', '', '', '', '']);
    setErrorMsg(null);
    setStatus('submitting');

    try {
      if (flowType === 'sign-in') {
        if (!signIn) return;
        const isEmailCodeFactor = (factor: SignInFirstFactor): factor is EmailCodeFactor =>
          factor.strategy === 'email_code';
        const emailCodeFactor = signIn.supportedFirstFactors?.find(isEmailCodeFactor);

        if (emailCodeFactor) {
          await signIn.prepareFirstFactor({
            strategy: 'email_code',
            emailAddressId: emailCodeFactor.emailAddressId,
          });
        }
      } else {
        if (!signUp) return;
        await signUp.prepareEmailAddressVerification({ strategy: 'email_code' });
      }

      setStatus('idle');
      setResendCooldown(30);
      otpInputRefs.current[0]?.focus();
    } catch (err: unknown) {
      setStatus('idle');
      setErrorMsg(extractClerkError(err));
    }
  };

  const handleSetupSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!fullName.trim() || !password || !confirmPassword) {
      setErrorMsg('Full name, password, and confirmation are required.');
      return;
    }

    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match.');
      return;
    }

    if (!isClerkLoaded || !signUp) return;

    setErrorMsg(null);
    setStatus('submitting');

    try {
      const parts = fullName.trim().split(' ');
      const firstName = parts[0];
      const lastName = parts.slice(1).join(' ') || undefined;

      const result = await signUp.update({
        firstName,
        lastName,
        password,
      });

      if (result.status === 'complete') {
        if (setActive) {
          await setActive({ session: result.createdSessionId });
        }
        navigate('/map', { replace: true });
      } else {
        setStatus('idle');
        setErrorMsg('Setup incomplete. Please review required fields.');
      }
    } catch (err: unknown) {
      setStatus('idle');
      setErrorMsg(extractClerkError(err));
    }
  };

  const handleChangeEmail = (): void => {
    setSearchParams({});
    setPassword('');
    setErrorMsg(null);
  };

  return {
    isSsoCallback,
    currentMode,
    modeContainerRef,
    email,
    otpDigits,
    otpInputRefs,
    resendCooldown,
    fullName,
    password,
    confirmPassword,
    status,
    activeOAuth,
    errorMsg,
    isBusy,
    setEmail,
    setFullName,
    setPassword,
    setConfirmPassword,
    handleEmailSubmit,
    handlePasswordSubmit,
    handleOAuthClick,
    handleOtpChange,
    handleOtpKeyDown,
    handleOtpPaste,
    handleOtpSubmit,
    handleResendOtp,
    handleSetupSubmit,
    handleChangeEmail,
    handleSwitchToOtpFromLogin,
  };
}
