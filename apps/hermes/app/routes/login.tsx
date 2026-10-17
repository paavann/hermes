import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router';
import type { MetaFunction } from 'react-router';
import gsap from 'gsap';
import { cn } from '@hermes/ui-components';

export const meta: MetaFunction = () => [
  { title: 'Login — Hermes Geospatial Intelligence' },
  {
    name: 'description',
    content: 'Authenticate into the Hermes geospatial intelligence platform.',
  },
];

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

  // 1:1 true square height matching column width, automatically increasing row count to fill height
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

export function LoginCheckerboardPattern(): React.JSX.Element {
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

  const hasAnimatedRef = useRef<boolean>(false);

  // Trigger animation when in view (only once, never reset or hide during scroll)
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
          if (entry.isIntersecting) {
            setIsInView(true);
          }
        });
      },
      { threshold: 0.05 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Random one-by-one GSAP reveal (runs once, stays visible forever)
  useEffect(() => {
    const boxes = tileRefs.current
      .slice(0, layout.cells.length)
      .filter((node): node is HTMLDivElement => node !== null);

    if (boxes.length === 0) return;

    if (isInView && !hasAnimatedRef.current) {
      hasAnimatedRef.current = true;
      gsap.killTweensOf(boxes);

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
    }
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

// ─── Animated GSAP Login Button ──────────────────────────────────────────────

interface LoginSubmitBtnProps {
  readonly isSubmitting?: boolean;
  readonly disabled?: boolean;
}

export function LoginSubmitBtn({
  isSubmitting = false,
  disabled = false,
}: LoginSubmitBtnProps): React.JSX.Element {
  const text1Ref = useRef<HTMLSpanElement>(null);
  const text2Ref = useRef<HTMLSpanElement>(null);
  const leftSquareRef = useRef<HTMLSpanElement>(null);
  const arrow1Ref = useRef<HTMLSpanElement>(null);
  const arrow2Ref = useRef<HTMLSpanElement>(null);
  const scanlineRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const text1 = text1Ref.current;
    const text2 = text2Ref.current;
    const leftSquare = leftSquareRef.current;
    const arrow1 = arrow1Ref.current;
    const arrow2 = arrow2Ref.current;
    const scanline = scanlineRef.current;

    if (leftSquare && arrow2 && scanline) {
      gsap.set(leftSquare, { x: -12, opacity: 0, rotation: -90 });
      gsap.set(arrow2, { x: -24, opacity: 0 });
      gsap.set(scanline, { scaleX: 0, transformOrigin: 'left center' });
    }
    return () => {
      gsap.killTweensOf([text1, text2, leftSquare, arrow1, arrow2, scanline]);
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
      aria-label="Log in"
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
          {isSubmitting ? 'AUTHENTICATING...' : 'LOG IN'}
        </span>
        <span ref={text2Ref} className="block leading-4 tracking-widest font-extrabold text-black">
          {isSubmitting ? 'AUTHENTICATING...' : 'LOG IN'}
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

// ─── Password Eye Toggle Button ──────────────────────────────────────────────

interface PasswordEyeToggleProps {
  readonly show: boolean;
  readonly onToggle: () => void;
  readonly ariaLabel: string;
}

function PasswordEyeToggle({
  show,
  onToggle,
  ariaLabel,
}: PasswordEyeToggleProps): React.JSX.Element {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute right-3.5 top-1/2 -translate-y-1/2 z-20 text-slate-muted hover:text-white transition-colors cursor-pointer p-1 flex items-center justify-center focus:outline-none"
      aria-label={ariaLabel}
      tabIndex={0}
    >
      {show ? (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-4 h-4 block"
          aria-hidden="true"
        >
          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
          <line x1="1" y1="1" x2="23" y2="23" />
        </svg>
      ) : (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-4 h-4 block"
          aria-hidden="true"
        >
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      )}
    </button>
  );
}

// ─── Login Page Component ────────────────────────────────────────────────────

interface LoginFormState {
  readonly email: string;
  readonly password: string;
}

export default function Login(): React.JSX.Element {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<LoginFormState>({
    email: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [status, setStatus] = useState<'idle' | 'submitting'>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    if (!formData.email.trim() || !formData.password.trim()) {
      setErrorMsg('Email and password are required.');
      return;
    }

    setErrorMsg(null);
    setStatus('submitting');

    setTimeout(() => {
      setStatus('idle');
      navigate('/map');
    }, 600);
  };

  return (
    <div className="min-h-screen w-full bg-obsidian text-slate-muted font-mono selection:bg-neon-blue/20 selection:text-neon-blue flex flex-col lg:flex-row overflow-x-hidden relative">
      {/* Left Side: Header + Centered Login Form (~70% width on desktop, matching reference layout) */}
      <div className="w-full lg:w-[70%] min-h-screen flex flex-col justify-between px-6 sm:px-12 md:px-16 pt-24 pb-12 relative z-10">
        {/* Top-Left Brand Link (fixed with opaque background so scrolled content passes underneath invisibly) */}
        <header
          role="banner"
          className="fixed top-0 left-0 w-full lg:w-[70%] z-30 bg-obsidian px-6 sm:px-12 md:px-16 py-7 flex items-center"
        >
          <Link
            to="/"
            aria-label="Hermes Home"
            className="font-bold tracking-[0.25em] text-sm text-ivory hover:text-white transition-colors"
          >
            HERMES
          </Link>
        </header>

        {/* Centered Login Container */}
        <main className="w-full max-w-[380px] mx-auto my-auto py-12 flex flex-col items-center">
          {/* Monumental Hermes Logo (sized to match the eye-hand illustration in the reference) */}
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

          {/* Welcome Heading */}
          <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-8">
            Welcome back!
          </h1>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="w-full space-y-5" noValidate>
            {/* Email Field */}
            <div>
              <label
                htmlFor="login-email"
                className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
              >
                Email
              </label>
              <input
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, email: e.target.value }))
                }
                placeholder="operator@hermes.intel"
                className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none"
              />
            </div>

            {/* Password Field (with eye toggle) */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label
                  htmlFor="login-password"
                  className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono"
                >
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-[11px] text-neon-blue/90 hover:text-neon-blue transition-colors font-mono"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={formData.password}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, password: e.target.value }))
                  }
                  placeholder="••••••••••••"
                  className="w-full bg-black/60 border border-white/10 px-4 py-3 pr-11 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none"
                />
                <PasswordEyeToggle
                  show={showPassword}
                  onToggle={() => setShowPassword((prev) => !prev)}
                  ariaLabel={showPassword ? 'Hide password' : 'Show password'}
                />
              </div>
              <p className="mt-2 text-[11px] text-slate-muted/50 font-mono leading-relaxed">
                6+ characters, one number, and one capital letter
              </p>
            </div>

            {/* Validation Error */}
            {errorMsg && (
              <div className="text-xs text-rose-400 font-mono tracking-wide">
                [ ERROR // {errorMsg} ]
              </div>
            )}

            {/* Animated Login Button */}
            <div className="pt-1">
              <LoginSubmitBtn isSubmitting={status === 'submitting'} />
            </div>
          </form>

          {/* Bottom Sign Up Link */}
          <div className="mt-7 text-xs text-slate-muted/70 font-mono text-center">
            <span>New to Hermes? </span>
            <Link
              to="/sign-up"
              className="text-ivory hover:text-neon-blue underline underline-offset-4 transition-colors font-medium"
            >
              Sign up
            </Link>
          </div>
        </main>

        {/* Bottom spacer to keep form vertically balanced */}
        <div className="h-5" aria-hidden="true" />
      </div>

      {/* Right Side: Borderless, Background-Free Alternating Corner-Connected 1:1 Squares (~30% width) */}
      <aside
        aria-label="Geometric pattern panel"
        className="hidden lg:block fixed right-0 top-0 bottom-0 w-[30%] h-screen overflow-hidden pointer-events-none z-0"
      >
        <LoginCheckerboardPattern />
      </aside>
    </div>
  );
}