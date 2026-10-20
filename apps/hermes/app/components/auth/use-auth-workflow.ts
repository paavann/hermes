import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams, useLocation, useParams } from 'react-router';
import gsap from 'gsap';
import type { OAuthProviderId } from '@hermes/ui-components';
import type { AuthMode, AuthStatus } from './types';
import {
  getStoredEmail,
  setStoredEmail,
  clearStoredEmail,
  getStoredOnboardingToken,
  setStoredOnboardingToken,
  clearStoredOnboardingToken,
  isKnownUserEmail,
  markUserEmailAsKnown,
} from './auth-storage';

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
  readonly fallbackPassword: string;
  readonly status: AuthStatus;
  readonly activeOAuth: OAuthProviderId | null;
  readonly errorMsg: string | null;
  readonly isBusy: boolean;
  readonly setEmail: (email: string) => void;
  readonly setFullName: (name: string) => void;
  readonly setPassword: (password: string) => void;
  readonly setConfirmPassword: (password: string) => void;
  readonly setFallbackPassword: (password: string) => void;
  readonly handleEmailSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly handleOAuthClick: (providerId: OAuthProviderId) => void;
  readonly handleOtpChange: (index: number, rawValue: string) => void;
  readonly handleOtpKeyDown: (index: number, e: React.KeyboardEvent<HTMLInputElement>) => void;
  readonly handleOtpPaste: (e: React.ClipboardEvent<HTMLInputElement>) => void;
  readonly handleOtpSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly handleResendOtp: () => void;
  readonly handleSetupSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly handleFallbackPasswordSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly handleChangeEmail: () => void;
  readonly handleUsePassword: () => void;
  readonly handleBackToOtp: () => void;
}

export function useAuthWorkflow(): UseAuthWorkflowReturn {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const modeContainerRef = useRef<HTMLDivElement | null>(null);

  const isSsoCallback =
    params['*'] === 'sso-callback' ||
    location.pathname.endsWith('/sso-callback') ||
    searchParams.get('mode') === 'sso-callback';

  const rawMode = searchParams.get('mode');
  const currentMode: AuthMode =
    rawMode === 'otp' || rawMode === 'setup' || rawMode === 'password'
      ? rawMode
      : 'email';

  const [email, setEmail] = useState<string>(() => getStoredEmail());
  const [onboardingToken, setOnboardingToken] = useState<string | null>(() =>
    getStoredOnboardingToken()
  );

  const [otpDigits, setOtpDigits] = useState<string[]>(['', '', '', '', '', '']);
  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [resendCooldown, setResendCooldown] = useState<number>(0);

  const [fullName, setFullName] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [fallbackPassword, setFallbackPassword] = useState<string>('');

  const [status, setStatus] = useState<AuthStatus>('idle');
  const [activeOAuth, setActiveOAuth] = useState<OAuthProviderId | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isBusy = status === 'submitting' || activeOAuth !== null;

  useEffect(() => {
    setStoredEmail(email);
  }, [email]);

  useEffect(() => {
    setStoredOnboardingToken(onboardingToken);
  }, [onboardingToken]);

  useEffect(() => {
    if (isSsoCallback) return;

    const storedEmail = email.trim() || getStoredEmail();
    const storedToken = onboardingToken || getStoredOnboardingToken();

    if ((currentMode === 'otp' || currentMode === 'password') && !storedEmail) {
      setSearchParams({}, { replace: true });
      return;
    }

    if (currentMode === 'setup' && (!storedEmail || !storedToken)) {
      setSearchParams(storedEmail ? { mode: 'otp' } : {}, { replace: true });
    }
  }, [currentMode, email, onboardingToken, setSearchParams, isSsoCallback]);

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
  }, [currentMode, isSsoCallback]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = window.setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendCooldown]);

  const handleEmailSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const trimmedEmail = email.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!trimmedEmail || !emailRegex.test(trimmedEmail)) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    setErrorMsg(null);
    setStatus('submitting');

    window.setTimeout(() => {
      setStatus('idle');
      setOtpDigits(['', '', '', '', '', '']);
      setResendCooldown(30);
      setSearchParams({ mode: 'otp' });
    }, 450);
  };

  const handleOAuthClick = (providerId: OAuthProviderId): void => {
    if (isBusy) return;
    setErrorMsg(null);
    setActiveOAuth(providerId);

    window.setTimeout(() => {
      setActiveOAuth(null);
      navigate('/map', { replace: true });
    }, 600);
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

  const handleOtpSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const code = otpDigits.join('');
    if (code.length < 6) {
      setErrorMsg('Please enter all 6 digits of your verification code.');
      return;
    }

    setErrorMsg(null);
    setStatus('submitting');

    window.setTimeout(() => {
      setStatus('idle');
      const isExistingUser = isKnownUserEmail(email);

      if (isExistingUser) {
        clearStoredEmail();
        clearStoredOnboardingToken();
        navigate('/map', { replace: true });
      } else {
        const tempToken = `ob_${Date.now()}`;
        setOnboardingToken(tempToken);
        setStoredOnboardingToken(tempToken);
        setSearchParams({ mode: 'setup' }, { replace: true });
      }
    }, 500);
  };

  const handleResendOtp = (): void => {
    if (resendCooldown > 0 || isBusy) return;
    setOtpDigits(['', '', '', '', '', '']);
    setErrorMsg(null);
    setResendCooldown(30);
    otpInputRefs.current[0]?.focus();
  };

  const handleSetupSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    if (!fullName.trim() || !password || !confirmPassword) {
      setErrorMsg('Full name, password, and confirmation are required.');
      return;
    }

    const hasMinLength = password.length >= 6;
    const hasNumber = /\d/.test(password);
    const hasCapital = /[A-Z]/.test(password);

    if (!hasMinLength || !hasNumber || !hasCapital) {
      setErrorMsg('Password requires 6+ characters, one number, and one capital letter.');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match.');
      return;
    }

    setErrorMsg(null);
    setStatus('submitting');

    window.setTimeout(() => {
      setStatus('idle');
      markUserEmailAsKnown(email);
      clearStoredEmail();
      clearStoredOnboardingToken();
      navigate('/map', { replace: true });
    }, 600);
  };

  const handleFallbackPasswordSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    if (!fallbackPassword.trim()) {
      setErrorMsg('Please enter your password.');
      return;
    }

    setErrorMsg(null);
    setStatus('submitting');

    window.setTimeout(() => {
      setStatus('idle');
      clearStoredEmail();
      clearStoredOnboardingToken();
      navigate('/map', { replace: true });
    }, 500);
  };

  const handleChangeEmail = (): void => {
    setSearchParams({});
  };

  const handleUsePassword = (): void => {
    setSearchParams({ mode: 'password' });
  };

  const handleBackToOtp = (): void => {
    setSearchParams({ mode: 'otp' });
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
    fallbackPassword,
    status,
    activeOAuth,
    errorMsg,
    isBusy,
    setEmail,
    setFullName,
    setPassword,
    setConfirmPassword,
    setFallbackPassword,
    handleEmailSubmit,
    handleOAuthClick,
    handleOtpChange,
    handleOtpKeyDown,
    handleOtpPaste,
    handleOtpSubmit,
    handleResendOtp,
    handleSetupSubmit,
    handleFallbackPasswordSubmit,
    handleChangeEmail,
    handleUsePassword,
    handleBackToOtp,
  };
}
