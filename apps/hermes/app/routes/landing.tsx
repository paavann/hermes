import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router';
import type { MetaFunction } from 'react-router';
import gsap from 'gsap';
import { cn } from '@hermes/ui-components';
import earthOrbitImg from '../assets/earth-orbit.jpg';

export const meta: MetaFunction = () => [
  { title: 'Hermes — Geospatial Intelligence Platform' },
  {
    name: 'description',
    content:
      "Provably grounded real-time geospatial intelligence. Observe the world's critical events unfold across space and causal time.",
  },
  { property: 'og:title', content: 'Hermes — Geospatial Intelligence Platform' },
  {
    property: 'og:description',
    content: 'Autonomous geospatial news intelligence with vector consensus and causal lineage.',
  },
];

// ─── Types ───────────────────────────────────────────────────────────────────

interface NavItem {
  readonly id: string;
  readonly label: string;
  readonly href: string;
}

const NAV_ITEMS: readonly NavItem[] = [
  { id: 'home', label: 'Home', href: '#hero' },
  { id: 'problem', label: 'The Problem', href: '#problem' },
  { id: 'capabilities', label: 'Capabilities', href: '#capabilities' },
  { id: 'access', label: 'Access', href: '#access' },
] as const;

// ─── Launch Map GSAP Button ──────────────────────────────────────────────────

interface LaunchMapBtnProps {
  readonly className?: string;
}

export function LaunchMapBtn({ className }: LaunchMapBtnProps): React.JSX.Element {
  const text1Ref = useRef<HTMLSpanElement>(null);
  const text2Ref = useRef<HTMLSpanElement>(null);

  const handleMouseEnter = (): void => {
    if (!text1Ref.current || !text2Ref.current) return;
    gsap.killTweensOf([text1Ref.current, text2Ref.current]);
    gsap.to(text1Ref.current, {
      yPercent: -100,
      duration: 0.32,
      ease: 'power3.out',
    });
    gsap.to(text2Ref.current, {
      yPercent: -100,
      duration: 0.32,
      ease: 'power3.out',
    });
  };

  const handleMouseLeave = (): void => {
    if (!text1Ref.current || !text2Ref.current) return;
    gsap.killTweensOf([text1Ref.current, text2Ref.current]);
    gsap.to(text1Ref.current, {
      yPercent: 0,
      duration: 0.28,
      ease: 'power2.inOut',
    });
    gsap.to(text2Ref.current, {
      yPercent: 0,
      duration: 0.28,
      ease: 'power2.inOut',
    });
  };

  return (
    <Link
      to="/map"
      id="nav-launch-map"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={cn(
        'group relative inline-flex items-center justify-center overflow-hidden bg-ivory text-obsidian px-4 py-1.5 font-mono text-xs font-bold uppercase tracking-wider transition-colors duration-200 hover:bg-white',
        className
      )}
      aria-label="Launch the intelligence map"
    >
      <div className="relative h-4 overflow-hidden flex flex-col items-center justify-start">
        <span ref={text1Ref} className="block leading-4">
          LAUNCH MAP
        </span>
        <span ref={text2Ref} className="block leading-4 text-black font-extrabold">
          LAUNCH MAP ↗
        </span>
      </div>
    </Link>
  );
}

// ─── Navigation Component ───────────────────────────────────────────────────

interface NavProps {
  readonly activeSection?: string;
}

export function Nav({ activeSection = 'home' }: NavProps): React.JSX.Element {
  const [scrolled, setScrolled] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  useEffect(() => {
    const handleScroll = (): void => {
      setScrolled(window.scrollY > 20);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      id="site-header"
      role="banner"
      className="fixed top-0 left-0 right-0 z-40 h-[62px] font-mono pointer-events-none"
    >
      <div className="w-full h-full flex items-center">
        {/* Left column (matches fixed vertical grid line, NO bottom border so line runs seamlessly) */}
        <div className="w-[180px] md:w-[220px] shrink-0 h-full pl-5 md:pl-8 pr-4 flex items-center pointer-events-auto">
          <Link
            to="/"
            aria-label="Hermes Home"
            className="font-bold tracking-[0.25em] text-sm text-ivory hover:text-white transition-colors"
          >
            HERMES
          </Link>
        </div>

        {/* Right column: Navigation links + Action buttons */}
        <div
          className={cn(
            'flex-1 h-full pl-5 md:pl-8 pr-5 md:pr-8 flex items-center justify-between min-w-0 pointer-events-auto transition-colors duration-250',
            scrolled
              ? 'bg-obsidian/85 backdrop-blur-md border-b border-border-subtle shadow-[0_4px_30px_rgba(0,0,0,0.5)]'
              : 'bg-transparent'
          )}
        >
          {/* Desktop Nav Links */}
          <nav aria-label="Primary navigation" className="hidden md:flex items-center gap-2">
            {NAV_ITEMS.map((item) => {
              const isActive = activeSection === item.id;
              const isHovered = hoveredItem === item.id;
              const showSquare = isActive || isHovered;

              return (
                <a
                  key={item.id}
                  href={item.href}
                  onMouseEnter={() => setHoveredItem(item.id)}
                  onMouseLeave={() => setHoveredItem(null)}
                  className={cn(
                    'group flex items-center gap-1.5 px-3 py-1.5 text-xs uppercase tracking-wider transition-colors',
                    isActive
                      ? 'text-ivory font-medium'
                      : 'text-slate-muted hover:text-ivory'
                  )}
                >
                  <span
                    className={cn(
                      'text-[9px] transition-colors',
                      showSquare ? 'text-neon-blue' : 'text-slate-muted/60'
                    )}
                    aria-hidden="true"
                  >
                    {showSquare ? '■' : '/'}
                  </span>
                  <span>{item.label}</span>
                </a>
              );
            })}
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-5 ml-auto">
            {/* Login Link */}
            <Link
              to="/login"
              className="text-xs uppercase tracking-wider text-slate-muted hover:text-ivory transition-colors"
            >
              LOGIN
            </Link>

            {/* Launch Map CTA with GSAP roll animation */}
            <LaunchMapBtn />

            {/* Mobile Menu Toggle Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="md:hidden flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-muted hover:text-ivory border border-border-subtle bg-black/40 transition-colors"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              <span className="text-neon-blue text-[9px]" aria-hidden="true">
                {mobileMenuOpen ? '■' : '/'}
              </span>
              <span>{mobileMenuOpen ? 'CLOSE' : 'MENU'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-border-subtle bg-obsidian/95 backdrop-blur-xl px-5 py-4 flex flex-col gap-2 pointer-events-auto">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.id}
              href={item.href}
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-2 py-2 text-xs uppercase tracking-wider text-slate-muted hover:text-ivory border-b border-white/5"
            >
              <span className="text-neon-blue text-[9px]">/</span>
              <span>{item.label}</span>
            </a>
          ))}
          <Link
            to="/login"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center gap-2 py-2 text-xs uppercase tracking-wider text-slate-muted hover:text-ivory"
          >
            <span className="text-neon-blue text-[9px]">/</span>
            <span>LOGIN</span>
          </Link>
        </div>
      )}
    </header>
  );
}

// ─── Step 1 Scaffold Landing Page ───────────────────────────────────────────

export default function Landing(): React.JSX.Element {
  return (
    <div className="min-h-screen bg-obsidian text-slate-muted font-mono selection:bg-neon-blue/20 selection:text-neon-blue relative">
      {/* Atalanta-inspired Persistent Left Margin Line (Desktop) */}
      <div
        className="hidden md:block fixed top-0 bottom-0 left-[180px] md:left-[220px] w-px bg-white/10 z-50 pointer-events-none"
        aria-hidden="true"
      />

      {/* Fixed Minimalist Navigation Bar */}
      <Nav activeSection="home" />

      {/* Main Content Container */}
      <main id="main-content" className="pt-[62px]">
        {/* Section: Hero Frame */}
        <section id="hero" className="relative w-full">
          {/* Top Heading Area (aligned with the left line at 180px/220px) */}
          <div className="w-full pl-5 md:pl-[240px] pr-5 md:pr-8 pt-14 md:pt-20 pb-12 md:pb-16 max-w-6xl">
            <div className="text-xs uppercase tracking-[0.2em] text-slate-muted/70 mb-4 flex items-center gap-2">
              <span className="text-neon-blue">■</span>
              <span>Hermes Intelligence</span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-medium tracking-tight text-slate-muted leading-tight">
              Global event observability for{' '}
              <span className="text-ivory font-bold">
                the world's most critical decisions.
              </span>
            </h1>
          </div>

          {/* Full-Width Earth Orbital Frame peeking into the hero fold */}
          <div className="relative w-full border-t border-b border-border-subtle bg-black overflow-hidden">
            {/* Earth Media Layer (Spans full width, line at 220px passes right over it) */}
            <div className="relative w-full aspect-[16/10] md:aspect-[21/10] min-h-[460px] md:min-h-[580px] lg:min-h-[640px] overflow-hidden">
              <img
                src={earthOrbitImg}
                alt="Earth orbital satellite view"
                className="w-full h-full object-cover object-top opacity-85"
                loading="eager"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-obsidian/90 via-obsidian/40 to-transparent" />
              <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-transparent to-obsidian/30" />

              {/* Overlaid Hero Content (Personal surface-level copy) */}
              <div className="absolute inset-0 flex flex-col justify-between pl-5 md:pl-[240px] pr-5 md:pr-8 py-10 md:py-16 max-w-4xl z-10 pointer-events-auto">
                <div className="pt-2 md:pt-4">
                  <p className="text-base sm:text-lg md:text-xl text-slate-muted leading-relaxed max-w-2xl md:max-w-3xl">
                    I built Hermes to change how you experience the world. Instead of getting lost
                    in overwhelming feeds and endless headlines, observe critical global events
                    unfold in real time—with spatial context and quiet clarity.
                  </p>
                </div>

                {/* Bottom Telemetry Tag */}
                <div className="text-[10px] text-slate-muted/70 uppercase tracking-widest font-mono flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-neon-blue inline-block animate-pulse" />
                  <span>SYS // ORBITAL OBSERVABILITY • SRID 4326</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Section: The Problem */}
        <section
          id="problem"
          className="min-h-[60vh] border-b border-border-subtle flex"
        >
          {/* Left Sidebar: Section Title */}
          <div className="w-[180px] md:w-[220px] shrink-0 p-5 md:p-8 hidden md:block">
            <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2 sticky top-24">
              <span className="text-neon-blue">■</span>
              <span>The Problem</span>
            </h2>
          </div>

          {/* Right Column: Content */}
          <div className="flex-1 p-5 md:p-8 py-20 md:py-24 max-w-4xl">
            <div className="space-y-8 text-lg sm:text-2xl text-slate-muted leading-relaxed">
              <p>
                The world moves in physical coordinates, yet news consumption remains trapped in
                linear, text-heavy feeds designed for engagement rather than spatial comprehension.
              </p>
            </div>
          </div>
        </section>

        {/* Section: Capabilities */}
        <section
          id="capabilities"
          className="min-h-[60vh] border-b border-border-subtle flex"
        >
          <div className="w-[180px] md:w-[220px] shrink-0 p-5 md:p-8 hidden md:block">
            <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2 sticky top-24">
              <span className="text-neon-blue">■</span>
              <span>Capabilities</span>
            </h2>
          </div>
          <div className="flex-1 p-5 md:p-8 py-20 md:py-24 max-w-4xl">
            <p className="text-sm uppercase tracking-wider text-slate-muted/60">
              [Core Capability Cards will be implemented in Step 5]
            </p>
          </div>
        </section>

        {/* Section: Access */}
        <section
          id="access"
          className="min-h-[50vh] border-b border-border-subtle flex"
        >
          <div className="w-[180px] md:w-[220px] shrink-0 p-5 md:p-8 hidden md:block">
            <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2 sticky top-24">
              <span className="text-neon-blue">■</span>
              <span>Access</span>
            </h2>
          </div>
          <div className="flex-1 p-5 md:p-8 py-20 md:py-24 max-w-4xl">
            <p className="text-sm uppercase tracking-wider text-slate-muted/60">
              [Access & Terminal Form will be implemented in Step 6]
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border-subtle flex">
        <div className="w-[180px] md:w-[220px] shrink-0 p-5 md:p-8 hidden md:block" />
        <div className="flex-1 p-5 md:p-8 py-10 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-muted/60 gap-4">
          <div>© {new Date().getFullYear()} HERMES GEOINT INC. ALL RIGHTS RESERVED.</div>
          <div className="flex items-center gap-4">
            <Link to="/map" className="hover:text-ivory transition-colors">MAP</Link>
            <span className="text-white/10">/</span>
            <a href="#hero" className="hover:text-ivory transition-colors">TOP ↑</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
