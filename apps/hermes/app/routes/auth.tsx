import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useSearchParams, useLocation, useParams } from 'react-router';
import type { MetaFunction } from 'react-router';
import { HandleSSOCallback } from '@clerk/react-router';
import gsap from 'gsap';
import { cn } from '@hermes/ui-components';

export const meta: MetaFunction = ({ location }) => {
  const isSso = location?.pathname?.includes('/sso-callback');
  return [
    {
      title: isSso
        ? 'SSO Verification — Hermes Geospatial Intelligence'
        : 'Authenticate — Hermes Geospatial Intelligence',
    },
    {
      name: 'description',
      content: 'Authenticate into the Hermes geospatial intelligence platform.',
    },
  ];
};

// ─── Storage Keys for Reload Resilience & Flow Guards ────────────────────────

const STORAGE_EMAIL_KEY = 'hermes_auth_email';
const STORAGE_ONBOARDING_TOKEN_KEY = 'hermes_onboarding_token';
const STORAGE_KNOWN_USERS_KEY = 'hermes_known_emails';

type AuthMode = 'email' | 'otp' | 'setup' | 'password';

// ─── Right-Side Corner-Connected Checkerboard Squares ────────────────────────

interface SquareCell {
  readonly id: string;
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

interface CheckerboardLayout {
  readonly cells: readonly SquareCell[];
}

function computeCheckerboardLayout(width: number, height: number): CheckerboardLayout {
  const safeWidth = Math.max(width, 240);
  const safeHeight = Math.max(height, 600);

  // 5-6 columns across the pattern space (5 on narrower panels, 6 on standard/wide desktop)
  const colCount = safeWidth >= 380 ? 4 : 3;

  // Distribute integer pixel widths evenly so adjacent corners meet with zero gaps
  const colLefts: number[] = [];
  const colWidths: number[] = [];
  for (let c = 0; c < colCount; c += 1) {
    const left = Math.round((c * safeWidth) / colCount);
    const right = Math.round(((c + 1) * safeWidth) / colCount);
    colLefts.push(left);
    colWidths.push(right - left);
  }

  // 1:1 true square height matching column width, automatically scaling row count to fill height
  const squareSize = Math.max(Math.round(safeWidth / colCount), 24);
  const rowCount = Math.ceil(safeHeight / squareSize) + 1;

  const cells: SquareCell[] = [];

  for (let r = 0; r < rowCount; r += 1) {
    for (let c = 0; c < colCount; c += 1) {
      // Strictly alternating checkerboard so squares only ever touch at their corners
      if ((r + c) % 2 === 0) {
        cells.push({
          id: `sq-r${r}-c${c}`,
          left: colLefts[c],
          top: r * squareSize,
          width: colWidths[c],
          height: squareSize,
        });
      }
    }
  }

  return { cells };
}

export function AuthCheckerboardPattern(): React.JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const tileRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [layout, setLayout] = useState<CheckerboardLayout>(() =>
    computeCheckerboardLayout(440, 960)
  );
  const [isInView, setIsInView] = useState<boolean>(false);

  // Measure panel dimensions so squares always fill 100% of the right-side space
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let lastWidth = el.clientWidth || Math.round(window.innerWidth * 0.3);
    let lastHeight = el.clientHeight || window.innerHeight;
    setLayout(computeCheckerboardLayout(lastWidth, lastHeight));

    const handleResize = (): void => {
      const newWidth = el.clientWidth || Math.round(window.innerWidth * 0.3);
      const newHeight = el.clientHeight || window.innerHeight;
      if (
        newWidth > 0 &&
        newHeight > 0 &&
        (Math.abs(newWidth - lastWidth) > 2 || Math.abs(newHeight - lastHeight) > 2)
      ) {
        lastWidth = newWidth;
        lastHeight = newHeight;
        setLayout(computeCheckerboardLayout(newWidth, newHeight));
      }
    };

    if (typeof ResizeObserver !== 'undefined') {
      const resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(el);
      return () => resizeObserver.disconnect();
    } else {
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, []);

  // Trigger animation when in view
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (typeof window === 'undefined' || typeof window.IntersectionObserver === 'undefined') {
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          setIsInView(entry.isIntersecting);
        });
      },
      { threshold: 0.1 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Random one-by-one GSAP reveal (placement stays fixed, only reveal order is randomized)
  useEffect(() => {
    const boxes = tileRefs.current
      .slice(0, layout.cells.length)
      .filter((node): node is HTMLDivElement => node !== null);

    if (boxes.length === 0) return;

    gsap.killTweensOf(boxes);

    if (isInView) {
      const shuffled = [...boxes];
      for (let i = shuffled.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }

      gsap.fromTo(
        shuffled,
        { autoAlpha: 0, scale: 0.94 },
        {
          autoAlpha: 1,
          scale: 1,
          duration: 0.45,
          stagger: 0.025,
          ease: 'power3.out',
          overwrite: 'auto',
        }
      );
    } else {
      gsap.set(boxes, { autoAlpha: 0, scale: 0.94 });
    }

    return () => {
      gsap.killTweensOf(boxes);
    };
  }, [layout, isInView]);

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className="w-full h-full relative overflow-hidden select-none pointer-events-none"
    >
      {layout.cells.map((cell, idx) => (
        <div
          key={cell.id}
          ref={(node) => {
            tileRefs.current[idx] = node;
          }}
          style={{
            left: `${cell.left}px`,
            top: `${cell.top}px`,
            width: `${cell.width}px`,
            height: `${cell.height}px`,
          }}
          className="absolute bg-white/[0.035] border border-white/[0.04] opacity-0 will-change-transform"
        />
      ))}
    </div>
  );
}

// ─── Social OAuth Providers (Google, Facebook, Twitter/X, Microsoft) ─────────

type OAuthProviderId = 'google' | 'facebook' | 'x' | 'microsoft';

interface OAuthProvider {
  readonly id: OAuthProviderId;
  readonly label: string;
  readonly icon: React.JSX.Element;
}

const OAUTH_PROVIDERS: readonly OAuthProvider[] = [
  {
    id: 'google',
    label: 'Google',
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
        <path d="M21.35 11.1h-9.17v2.73h6.51c-.33 1.81-1.5 3.34-3.2 4.37v3.62h5.18c3.03-2.79 4.78-6.9 4.78-11.77 0-.8-.08-1.57-.23-2.31l.13.36z" />
        <path d="M12.18 22c4.32 0 7.95-1.43 10.6-3.88l-5.18-3.62c-1.43.96-3.26 1.53-5.42 1.53-4.17 0-7.7-2.81-8.96-6.59H-.13v3.73C2.51 18.41 7 22 12.18 22z" />
        <path d="M3.22 13.44c-.32-.96-.5-1.99-.5-3.05s.18-2.09.5-3.05V3.61H-.13C-1.2 5.75-1.82 8.16-1.82 10.39s.62 4.64 1.69 6.78l3.35-3.73z" />
        <path d="M12.18 4.75c2.35 0 4.46.81 6.12 2.4l4.59-4.59C20.12.98 16.5 0 12.18 0 7 0 2.51 3.59-.13 8.83l3.35 3.73c1.26-3.78 4.79-6.59 8.96-6.59z" />
      </svg>
    ),
  },
  {
    id: 'facebook',
    label: 'Facebook',
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
        <path d="M22.675 0H1.325C.593 0 0 .593 0 1.325v21.351C0 23.407.593 24 1.325 24H12.82v-9.294H9.692v-3.622h3.128V8.413c0-3.1 1.893-4.788 4.659-4.788 1.325 0 2.463.099 2.795.143v3.24l-1.918.001c-1.504 0-1.795.715-1.795 1.763v2.313h3.587l-.467 3.622h-3.12V24h6.116c.73 0 1.323-.593 1.323-1.325V1.325C24 .593 23.407 0 22.675 0z" />
      </svg>
    ),
  },
  {
    id: 'x',
    label: 'X / Twitter',
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
  },
  {
    id: 'microsoft',
    label: 'Microsoft',
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
        <rect x="2" y="2" width="9.2" height="9.2" />
        <rect x="12.8" y="2" width="9.2" height="9.2" />
        <rect x="2" y="12.8" width="9.2" height="9.2" />
        <rect x="12.8" y="12.8" width="9.2" height="9.2" />
      </svg>
    ),
  },
] as const;

// ─── Animated GSAP Primary Action Button ─────────────────────────────────────

interface AuthSubmitBtnProps {
  readonly label: string;
  readonly loadingLabel?: string;
  readonly isSubmitting?: boolean;
  readonly disabled?: boolean;
}

export function AuthSubmitBtn({
  label,
  loadingLabel = 'PROCESSING...',
  isSubmitting = false,
  disabled = false,
}: AuthSubmitBtnProps): React.JSX.Element {
  const text1Ref = useRef<HTMLSpanElement>(null);
  const text2Ref = useRef<HTMLSpanElement>(null);
  const leftSquareRef = useRef<HTMLSpanElement>(null);
  const arrow1Ref = useRef<HTMLSpanElement>(null);
  const arrow2Ref = useRef<HTMLSpanElement>(null);
  const scanlineRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (leftSquareRef.current && arrow2Ref.current && scanlineRef.current) {
      gsap.set(leftSquareRef.current, { x: -12, opacity: 0, rotation: -90 });
      gsap.set(arrow2Ref.current, { x: -24, opacity: 0 });
      gsap.set(scanlineRef.current, { scaleX: 0, transformOrigin: 'left center' });
    }
    return () => {
      gsap.killTweensOf([
        text1Ref.current,
        text2Ref.current,
        leftSquareRef.current,
        arrow1Ref.current,
        arrow2Ref.current,
        scanlineRef.current,
      ]);
    };
  }, []);

  const handleMouseEnter = (): void => {
    if (isSubmitting || disabled) return;
    if (
      !text1Ref.current ||
      !text2Ref.current ||
      !leftSquareRef.current ||
      !arrow1Ref.current ||
      !arrow2Ref.current ||
      !scanlineRef.current
    )
      return;

    gsap.killTweensOf([
      text1Ref.current,
      text2Ref.current,
      leftSquareRef.current,
      arrow1Ref.current,
      arrow2Ref.current,
      scanlineRef.current,
    ]);

    // Roll label vertically
    gsap.to([text1Ref.current, text2Ref.current], {
      yPercent: -100,
      duration: 0.32,
      ease: 'power3.out',
    });

    // Lock-in left tactical square
    gsap.to(leftSquareRef.current, {
      x: 0,
      opacity: 1,
      rotation: 0,
      duration: 0.3,
      ease: 'back.out(1.7)',
    });

    // Projectile arrow cycle on the right
    gsap.to(arrow1Ref.current, {
      x: 24,
      opacity: 0,
      duration: 0.2,
      ease: 'power2.in',
    });

    gsap.fromTo(
      arrow2Ref.current,
      { x: -24, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.26, delay: 0.06, ease: 'power3.out' }
    );

    // Bottom scanline sweep
    gsap.to(scanlineRef.current, {
      scaleX: 1,
      duration: 0.36,
      ease: 'power3.out',
    });
  };

  const handleMouseLeave = (): void => {
    if (isSubmitting || disabled) return;
    if (
      !text1Ref.current ||
      !text2Ref.current ||
      !leftSquareRef.current ||
      !arrow1Ref.current ||
      !arrow2Ref.current ||
      !scanlineRef.current
    )
      return;

    gsap.killTweensOf([
      text1Ref.current,
      text2Ref.current,
      leftSquareRef.current,
      arrow1Ref.current,
      arrow2Ref.current,
      scanlineRef.current,
    ]);

    gsap.to([text1Ref.current, text2Ref.current], {
      yPercent: 0,
      duration: 0.26,
      ease: 'power2.inOut',
    });

    gsap.to(leftSquareRef.current, {
      x: -12,
      opacity: 0,
      rotation: -90,
      duration: 0.22,
      ease: 'power2.inOut',
    });

    gsap.to(arrow1Ref.current, {
      x: 0,
      opacity: 1,
      duration: 0.24,
      ease: 'power2.inOut',
    });

    gsap.to(arrow2Ref.current, {
      x: -24,
      opacity: 0,
      duration: 0.2,
      ease: 'power2.inOut',
    });

    gsap.to(scanlineRef.current, {
      scaleX: 0,
      duration: 0.26,
      ease: 'power2.inOut',
    });
  };

  const activeText = isSubmitting ? loadingLabel : label;

  return (
    <button
      type="submit"
      disabled={disabled || isSubmitting}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={cn(
        'group relative w-full bg-ivory text-black hover:bg-neon-blue hover:text-black transition-colors duration-200 py-3.5 px-6 text-xs uppercase tracking-widest font-bold font-mono flex items-center justify-between cursor-pointer rounded-none disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden',
        isSubmitting && 'bg-neon-blue text-black'
      )}
      aria-label={activeText}
    >
      {/* Left tactical square indicator */}
      <div className="relative flex items-center w-6">
        <span
          ref={leftSquareRef}
          className="text-[9px] text-black select-none pointer-events-none opacity-0"
          aria-hidden="true"
        >
          ■
        </span>
      </div>

      {/* Center rolling label */}
      <div className="relative h-4 overflow-hidden flex flex-col items-center justify-start select-none">
        <span ref={text1Ref} className="block leading-4 tracking-widest">
          {activeText}
        </span>
        <span ref={text2Ref} className="block leading-4 tracking-widest font-extrabold text-black">
          {activeText}
        </span>
      </div>

      {/* Right projectile arrow */}
      <div className="relative w-6 h-4 overflow-hidden flex items-center justify-end select-none pointer-events-none">
        <span ref={arrow1Ref} className="block text-sm leading-none">
          →
        </span>
        <span
          ref={arrow2Ref}
          className="absolute right-0 block text-sm leading-none opacity-0"
          aria-hidden="true"
        >
          →
        </span>
      </div>

      {/* Subtle bottom tactical sweep bar */}
      <span
        ref={scanlineRef}
        className="absolute bottom-0 left-0 right-0 h-[2px] bg-black/40 pointer-events-none"
        aria-hidden="true"
      />
    </button>
  );
}

// ─── Helper: Check / Save Known Users (For Local Testing Before API Hookup) ──

function isKnownUserEmail(email: string): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const raw = window.localStorage.getItem(STORAGE_KNOWN_USERS_KEY);
    if (!raw) return false;
    const list = JSON.parse(raw) as string[];
    return Array.isArray(list) && list.includes(email.trim().toLowerCase());
  } catch {
    return false;
  }
}

function markUserEmailAsKnown(email: string): void {
  if (typeof window === 'undefined') return;
  try {
    const normalized = email.trim().toLowerCase();
    const raw = window.localStorage.getItem(STORAGE_KNOWN_USERS_KEY);
    const list: string[] = raw ? (JSON.parse(raw) as string[]) : [];
    if (!list.includes(normalized)) {
      list.push(normalized);
      window.localStorage.setItem(STORAGE_KNOWN_USERS_KEY, JSON.stringify(list));
    }
  } catch {
    // Ignore storage quota errors
  }
}

// ─── Unified Progressive Auth Page Component ─────────────────────────────────

export default function Auth(): React.JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const modeContainerRef = useRef<HTMLDivElement | null>(null);

  // Detect SSO callback sub-route (/auth/sso-callback or ?mode=sso-callback)
  const isSsoCallback =
    params['*'] === 'sso-callback' ||
    location.pathname.endsWith('/sso-callback') ||
    searchParams.get('mode') === 'sso-callback';

  // Determine current mode from URL query param (?mode=otp | ?mode=setup | ?mode=password)
  const rawMode = searchParams.get('mode');
  const currentMode: AuthMode =
    rawMode === 'otp' || rawMode === 'setup' || rawMode === 'password'
      ? rawMode
      : 'email';

  // Persistent state across query-param modes
  const [email, setEmail] = useState<string>(() => {
    if (typeof window === 'undefined') return '';
    return window.sessionStorage.getItem(STORAGE_EMAIL_KEY) || '';
  });
  const [onboardingToken, setOnboardingToken] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    return window.sessionStorage.getItem(STORAGE_ONBOARDING_TOKEN_KEY);
  });

  // Step 2 (OTP) state: 6 individual digits
  const [otpDigits, setOtpDigits] = useState<string[]>(['', '', '', '', '', '']);
  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [resendCooldown, setResendCooldown] = useState<number>(0);

  // Step 3 (First-time Setup) state
  const [fullName, setFullName] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');

  // Fallback Password Login state
  const [fallbackPassword, setFallbackPassword] = useState<string>('');

  // Status & Feedback
  const [status, setStatus] = useState<'idle' | 'submitting'>('idle');
  const [activeOAuth, setActiveOAuth] = useState<OAuthProviderId | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isBusy = status === 'submitting' || activeOAuth !== null;

  // Sync email & onboardingToken with sessionStorage for reload resilience
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (email.trim()) {
      window.sessionStorage.setItem(STORAGE_EMAIL_KEY, email.trim());
    }
  }, [email]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (onboardingToken) {
      window.sessionStorage.setItem(STORAGE_ONBOARDING_TOKEN_KEY, onboardingToken);
    } else {
      window.sessionStorage.removeItem(STORAGE_ONBOARDING_TOKEN_KEY);
    }
  }, [onboardingToken]);

  // Route Guards: Prevent manual URL jumping without required prior state
  useEffect(() => {
    if (isSsoCallback) return;

    const storedEmail =
      email.trim() ||
      (typeof window !== 'undefined'
        ? window.sessionStorage.getItem(STORAGE_EMAIL_KEY) || ''
        : '');
    const storedToken =
      onboardingToken ||
      (typeof window !== 'undefined'
        ? window.sessionStorage.getItem(STORAGE_ONBOARDING_TOKEN_KEY)
        : null);

    if ((currentMode === 'otp' || currentMode === 'password') && !storedEmail) {
      setSearchParams({}, { replace: true });
      return;
    }

    if (currentMode === 'setup' && (!storedEmail || !storedToken)) {
      setSearchParams(storedEmail ? { mode: 'otp' } : {}, { replace: true });
    }
  }, [currentMode, email, onboardingToken, setSearchParams, isSsoCallback]);

  // Subtle GSAP transition when switching modes & auto-focus first input
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
      setTimeout(() => {
        otpInputRefs.current[0]?.focus();
      }, 40);
    }
  }, [currentMode, isSsoCallback]);

  // Countdown timer for "Resend code"
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = window.setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendCooldown]);

  // ─── Step 1 Handlers: Email & OAuth ────────────────────────────────────────

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

    // POST /api/v1/auth/otp/request { email: trimmedEmail }
    setTimeout(() => {
      setStatus('idle');
      setOtpDigits(['', '', '', '', '', '']);
      setResendCooldown(30);
      // Push ?mode=otp so browser Back button naturally returns to the email mode
      setSearchParams({ mode: 'otp' });
    }, 450);
  };

  const handleOAuthClick = (providerId: OAuthProviderId): void => {
    if (isBusy) return;
    setErrorMsg(null);
    setActiveOAuth(providerId);

    // GET /api/v1/auth/oauth/{providerId}
    setTimeout(() => {
      setActiveOAuth(null);
      navigate('/map', { replace: true });
    }, 600);
  };

  // ─── Step 2 Handlers: 6-Box OTP Verification ───────────────────────────────

  const handleOtpChange = (index: number, rawValue: string): void => {
    // Extract only digits
    const cleanDigits = rawValue.replace(/\D/g, '');

    if (!cleanDigits) {
      const next = [...otpDigits];
      next[index] = '';
      setOtpDigits(next);
      return;
    }

    // Handle multi-digit input or mobile autocomplete in a single box
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

    // POST /api/v1/auth/otp/verify { email, code }
    setTimeout(() => {
      setStatus('idle');

      // Check if returning user or first-time user:
      const isExistingUser = isKnownUserEmail(email);

      if (isExistingUser) {
        if (typeof window !== 'undefined') {
          window.sessionStorage.removeItem(STORAGE_EMAIL_KEY);
          window.sessionStorage.removeItem(STORAGE_ONBOARDING_TOKEN_KEY);
        }
        navigate('/map', { replace: true });
      } else {
        // First-time user -> issue temporary onboarding token and transition to ?mode=setup
        const tempToken = `ob_${Date.now()}`;
        setOnboardingToken(tempToken);
        if (typeof window !== 'undefined') {
          window.sessionStorage.setItem(STORAGE_ONBOARDING_TOKEN_KEY, tempToken);
        }
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

  // ─── Step 3 Handler: First-Time User Profile & Password Setup ──────────────

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

    // POST /api/v1/auth/onboarding { name: fullName, password, onboardingToken }
    setTimeout(() => {
      setStatus('idle');
      markUserEmailAsKnown(email);
      if (typeof window !== 'undefined') {
        window.sessionStorage.removeItem(STORAGE_EMAIL_KEY);
        window.sessionStorage.removeItem(STORAGE_ONBOARDING_TOKEN_KEY);
      }
      navigate('/map', { replace: true });
    }, 600);
  };

  // ─── Fallback Password Handler ─────────────────────────────────────────────

  const handleFallbackPasswordSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    if (!fallbackPassword.trim()) {
      setErrorMsg('Please enter your password.');
      return;
    }

    setErrorMsg(null);
    setStatus('submitting');

    // POST /api/v1/auth/password/verify { email, password: fallbackPassword }
    setTimeout(() => {
      setStatus('idle');
      if (typeof window !== 'undefined') {
        window.sessionStorage.removeItem(STORAGE_EMAIL_KEY);
        window.sessionStorage.removeItem(STORAGE_ONBOARDING_TOKEN_KEY);
      }
      navigate('/map', { replace: true });
    }, 500);
  };

  return (
    <div className="min-h-screen w-full bg-obsidian text-slate-muted font-mono selection:bg-neon-blue/20 selection:text-neon-blue flex flex-col lg:flex-row overflow-x-hidden">
      {/* Left Side: Header + Centered Progressive Auth Form (~70% width on desktop) */}
      <div className="w-full lg:w-[70%] min-h-screen flex flex-col justify-between px-6 sm:px-12 md:px-16 py-7 relative z-10">
        {/* Top-Left Brand Link */}
        <header role="banner" className="flex items-center">
          <Link
            to="/"
            aria-label="Hermes Home"
            className="font-bold tracking-[0.25em] text-sm text-ivory hover:text-white transition-colors"
          >
            HERMES
          </Link>
        </header>

        {/* Centered Auth Container */}
        <main className="w-full max-w-[390px] mx-auto my-auto py-12 flex flex-col items-center">
          {/* Monumental Hermes Logo */}
          <div className="w-[185px] sm:w-[205px] mb-6 text-[#8F8C7C] select-none pointer-events-none flex items-center justify-center">
            <svg
              viewBox="45 96 1370 284"
              fill="currentColor"
              className="w-full h-auto block"
              aria-label="Hermes"
              role="img"
            >
              {/* First Letter H: Left straight vertical stem */}
              <rect x="45" y="100" width="38" height="275" />

              {/* Horizontal Crossbar: Alternating up-down-up-down-up squares with touching edges */}
              <rect x="83" y="218" width="31" height="36" />
              <rect x="114" y="240" width="31" height="36" />
              <rect x="145" y="218" width="31" height="36" />
              <rect x="176" y="240" width="31" height="36" />
              <rect x="207" y="218" width="29" height="36" />

              {/* Right vertical stem */}
              <rect x="236" y="100" width="38" height="275" />

              {/* Lowercase 'ermes' in JetBrains Mono typography */}
              <text
                x="295"
                y="375"
                fontFamily="'JetBrains Mono', 'Fira Code', monospace"
                fontSize="375"
                fontWeight="700"
                letterSpacing="-0.04em"
              >
                ermes
              </text>
            </svg>
          </div>

          {/* Mode Content Wrapper */}
          <div ref={modeContainerRef} className="w-full flex flex-col items-center">
            {isSsoCallback ? (
              <div className="w-full flex flex-col items-center py-12 space-y-6">
                <div className="w-10 h-10 border border-neon-blue/40 border-t-neon-blue animate-spin" />
                <div className="text-center space-y-2">
                  <h1 className="text-xl font-bold text-ivory tracking-tight font-mono">
                    AUTHENTICATING SSO SESSION
                  </h1>
                  <p className="text-xs text-slate-muted font-mono tracking-wider">
                    [ SYSTEM // VERIFYING FEDERATED TOKENS ]
                  </p>
                </div>
                <HandleSSOCallback
                  navigateToApp={({ decorateUrl }) => {
                    const destination = decorateUrl('/map');
                    if (destination.startsWith('http')) {
                      window.location.href = destination;
                      return;
                    }
                    navigate(destination, { replace: true });
                  }}
                  navigateToSignIn={() => {
                    navigate('/auth', { replace: true });
                  }}
                  navigateToSignUp={() => {
                    navigate('/auth', { replace: true });
                  }}
                />
              </div>
            ) : (
              <>
                {/* ─── MODE 1: EMAIL + OAUTH OPTIONS ─────────────────────────────── */}
                {currentMode === 'email' && (
                  <>
                    <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-8">
                  Welcome to Hermes
                </h1>

                <form onSubmit={handleEmailSubmit} className="w-full space-y-5" noValidate>
                  <div>
                    <label
                      htmlFor="auth-email"
                      className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
                    >
                      Email
                    </label>
                    <input
                      id="auth-email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      disabled={isBusy}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="operator@hermes.intel"
                      className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
                    />
                  </div>

                  {errorMsg && (
                    <div className="text-xs text-rose-400 font-mono tracking-wide">
                      [ ERROR // {errorMsg} ]
                    </div>
                  )}

                  <div className="pt-1">
                    <AuthSubmitBtn
                      label="CONTINUE"
                      loadingLabel="DISPATCHING OTP..."
                      isSubmitting={status === 'submitting'}
                      disabled={isBusy}
                    />
                  </div>
                </form>

                {/* Tactical Divider */}
                <div
                  className="w-full flex items-center gap-3 my-6 select-none"
                  aria-hidden="true"
                >
                  <div className="h-px flex-1 bg-white/10" />
                  <span className="text-[10px] uppercase tracking-widest text-slate-muted/50 font-mono">
                    OR CONTINUE WITH
                  </span>
                  <div className="h-px flex-1 bg-white/10" />
                </div>

                {/* 4 OAuth Options: Google, Facebook, X/Twitter, Microsoft */}
                <div className="w-full grid grid-cols-2 gap-2.5">
                  {OAUTH_PROVIDERS.map((provider) => {
                    const isProviderLoading = activeOAuth === provider.id;

                    return (
                      <button
                        key={provider.id}
                        type="button"
                        disabled={isBusy}
                        onClick={() => handleOAuthClick(provider.id)}
                        className={cn(
                          'group relative flex items-center justify-center gap-2.5 bg-black/60 border border-white/10 hover:border-neon-blue/60 hover:bg-white/[0.04] px-3 py-2.5 text-xs text-slate-muted hover:text-ivory transition-all duration-200 font-mono rounded-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
                          isProviderLoading &&
                            'border-neon-blue text-neon-blue bg-neon-blue/5'
                        )}
                        aria-label={`Continue with ${provider.label}`}
                      >
                        <span className="text-slate-muted group-hover:text-ivory transition-colors">
                          {provider.icon}
                        </span>
                        <span className="tracking-wider uppercase text-[11px]">
                          {isProviderLoading ? 'CONNECTING...' : provider.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </>
            )}

            {/* ─── MODE 2: 6-DIGIT OTP VERIFICATION ──────────────────────────── */}
            {currentMode === 'otp' && (
              <>
                <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-2">
                  Check your inbox
                </h1>
                <div className="text-xs text-slate-muted/80 text-center mb-7 flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
                  <span>Enter the 6-digit code sent to</span>
                  <span className="text-ivory font-medium">{email}</span>
                  <button
                    type="button"
                    onClick={() => setSearchParams({})}
                    className="text-neon-blue hover:underline underline-offset-4 text-[11px] uppercase tracking-wider cursor-pointer"
                  >
                    [Change]
                  </button>
                </div>

                <form onSubmit={handleOtpSubmit} className="w-full space-y-6" noValidate>
                  {/* 6 Empty OTP Boxes */}
                  <div>
                    <label className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2.5 block">
                      Verification Code
                    </label>
                    <div className="grid grid-cols-6 gap-2 sm:gap-2.5">
                      {otpDigits.map((digit, idx) => (
                        <input
                          key={`otp-box-${idx}`}
                          ref={(el) => {
                            otpInputRefs.current[idx] = el;
                          }}
                          type="text"
                          inputMode="numeric"
                          autoComplete={idx === 0 ? 'one-time-code' : 'off'}
                          maxLength={6}
                          disabled={isBusy}
                          value={digit}
                          onChange={(e) => handleOtpChange(idx, e.target.value)}
                          onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                          onPaste={handleOtpPaste}
                          aria-label={`Digit ${idx + 1} of 6`}
                          className="w-full aspect-square bg-black/60 border border-white/10 text-center text-lg sm:text-xl font-bold text-ivory focus:border-neon-blue focus:bg-white/[0.03] focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
                        />
                      ))}
                    </div>
                  </div>

                  {errorMsg && (
                    <div className="text-xs text-rose-400 font-mono tracking-wide">
                      [ ERROR // {errorMsg} ]
                    </div>
                  )}

                  <div className="pt-1">
                    <AuthSubmitBtn
                      label="VERIFY & CONTINUE"
                      loadingLabel="VERIFYING OTP..."
                      isSubmitting={status === 'submitting'}
                      disabled={isBusy}
                    />
                  </div>
                </form>

                {/* Resend OTP & Fallback Password Links */}
                <div className="w-full mt-6 flex items-center justify-between text-[11px] text-slate-muted/70 font-mono">
                  <button
                    type="button"
                    disabled={resendCooldown > 0 || isBusy}
                    onClick={handleResendOtp}
                    className="hover:text-ivory transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  >
                    {resendCooldown > 0
                      ? `Resend code in ${resendCooldown}s`
                      : 'Resend code'}
                  </button>

                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => setSearchParams({ mode: 'password' })}
                    className="text-slate-muted/70 hover:text-neon-blue transition-colors underline underline-offset-4 cursor-pointer"
                  >
                    Use password instead
                  </button>
                </div>
              </>
            )}

            {/* ─── MODE 3: FIRST-TIME USER SETUP (NAME & PASSWORD) ───────────── */}
            {currentMode === 'setup' && (
              <>
                <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-2">
                  Complete your profile
                </h1>
                <p className="text-xs text-slate-muted/80 text-center mb-7">
                  Set up your operator credentials for{' '}
                  <span className="text-ivory font-medium">{email}</span>
                </p>

                <form onSubmit={handleSetupSubmit} className="w-full space-y-4" noValidate>
                  {/* Full Name */}
                  <div>
                    <label
                      htmlFor="setup-name"
                      className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
                    >
                      Full Name
                    </label>
                    <input
                      id="setup-name"
                      name="name"
                      type="text"
                      autoComplete="name"
                      required
                      disabled={isBusy}
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Elena Rostova"
                      className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
                    />
                  </div>

                  {/* Password */}
                  <div>
                    <label
                      htmlFor="setup-password"
                      className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
                    >
                      Password
                    </label>
                    <input
                      id="setup-password"
                      name="password"
                      type="password"
                      autoComplete="new-password"
                      required
                      disabled={isBusy}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
                    />
                    <p className="mt-1.5 text-[11px] text-slate-muted/50 font-mono leading-relaxed">
                      6+ characters, one number, and one capital letter
                    </p>
                  </div>

                  {/* Confirm Password */}
                  <div>
                    <label
                      htmlFor="setup-confirm-password"
                      className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
                    >
                      Confirm Password
                    </label>
                    <input
                      id="setup-confirm-password"
                      name="confirmPassword"
                      type="password"
                      autoComplete="new-password"
                      required
                      disabled={isBusy}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
                    />
                  </div>

                  {errorMsg && (
                    <div className="text-xs text-rose-400 font-mono tracking-wide">
                      [ ERROR // {errorMsg} ]
                    </div>
                  )}

                  <div className="pt-2">
                    <AuthSubmitBtn
                      label="COMPLETE SETUP"
                      loadingLabel="FINALIZING ACCOUNT..."
                      isSubmitting={status === 'submitting'}
                      disabled={isBusy}
                    />
                  </div>
                </form>
              </>
            )}

            {/* ─── FALLBACK MODE: PASSWORD LOGIN (?mode=password) ────────────── */}
            {currentMode === 'password' && (
              <>
                <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-2">
                  Enter your password
                </h1>
                <div className="text-xs text-slate-muted/80 text-center mb-7 flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
                  <span>Signing in as</span>
                  <span className="text-ivory font-medium">{email}</span>
                  <button
                    type="button"
                    onClick={() => setSearchParams({})}
                    className="text-neon-blue hover:underline underline-offset-4 text-[11px] uppercase tracking-wider cursor-pointer"
                  >
                    [Change]
                  </button>
                </div>

                <form
                  onSubmit={handleFallbackPasswordSubmit}
                  className="w-full space-y-5"
                  noValidate
                >
                  <div>
                    <label
                      htmlFor="fallback-password"
                      className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
                    >
                      Password
                    </label>
                    <input
                      id="fallback-password"
                      name="password"
                      type="password"
                      autoComplete="current-password"
                      required
                      disabled={isBusy}
                      value={fallbackPassword}
                      onChange={(e) => setFallbackPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
                    />
                  </div>

                  {errorMsg && (
                    <div className="text-xs text-rose-400 font-mono tracking-wide">
                      [ ERROR // {errorMsg} ]
                    </div>
                  )}

                  <div className="pt-1">
                    <AuthSubmitBtn
                      label="CONTINUE"
                      loadingLabel="AUTHENTICATING..."
                      isSubmitting={status === 'submitting'}
                      disabled={isBusy}
                    />
                  </div>
                </form>

                <div className="mt-6 text-center">
                  <button
                    type="button"
                    onClick={() => setSearchParams({ mode: 'otp' })}
                    className="text-[11px] text-slate-muted/70 hover:text-neon-blue transition-colors underline underline-offset-4 cursor-pointer font-mono"
                  >
                    ← Back to 6-digit OTP verification
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </main>

        {/* Bottom spacer to keep form vertically balanced */}
        <div className="h-5" aria-hidden="true" />
      </div>

      {/* Right Side: Borderless, Background-Free Alternating Corner-Connected 1:1 Squares (~30% width) */}
      <aside
        aria-label="Geometric pattern panel"
        className="hidden lg:block lg:w-[30%] h-screen sticky top-0 overflow-hidden"
      >
        <AuthCheckerboardPattern />
      </aside>
    </div>
  );
}