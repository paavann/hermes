import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router';
import type { MetaFunction } from 'react-router';
import gsap from 'gsap';
import { cn } from '@hermes/ui-components';
import earthOrbitImg from '../assets/earth-orbit.jpg';
import satelliteImg from '../assets/satellite.jpg';
import mapChartImg from '../assets/map-chart.jpg';
import darkTextureImg from '../assets/dark-texture.jpg';

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
  { id: 'contact', label: 'Contact', href: '#contact' },
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
      className="fixed top-0 left-0 right-0 z-50 h-[62px] font-mono pointer-events-none"
    >
      <div className="w-full h-full flex items-center">
        {/* Left column (matches fixed vertical grid line, NO bottom border so line runs seamlessly) */}
        <div
          className={cn(
            'w-[180px] md:w-[220px] shrink-0 h-full pl-5 md:pl-8 pr-4 flex items-center pointer-events-auto transition-colors duration-250',
            scrolled ? 'bg-obsidian/90 backdrop-blur-md' : 'bg-transparent'
          )}
        >
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

// ─── Section 2: Problem Statements & Scrollytelling ─────────────────────────

interface ProblemStatement {
  readonly id: string;
  readonly text: string;
}

const PROBLEM_STATEMENTS: readonly ProblemStatement[] = [
  {
    id: 'statement-1',
    text: 'The world moves in physical coordinates, yet our understanding of it remains trapped in linear text feeds designed for engagement rather than truth.',
  },
  {
    id: 'statement-2',
    text: 'Headlines tell you that something happened. They fail to show where it happened, how close it is to what matters, or what chain of events led there.',
  },
  {
    id: 'statement-3',
    text: 'Consuming hundreds of fragmented alerts creates noise and cognitive fatigue, not intelligence.',
  },
  {
    id: 'statement-4',
    text: 'To understand critical global shifts, we must observe them spatially—connecting geographic proximity, consensus, and causal history in a single unified view.',
  },
] as const;

interface PatternTile {
  readonly id: string;
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

interface PatternLayout {
  readonly containerHeight: number;
  readonly tiles: readonly PatternTile[];
}

function computePatternLayout(width: number, randomize = true): PatternLayout {
  const isDesktop = width >= 768;

  // 3 rows across 4 columns (desktop) or 3 columns (mobile)
  const colCount = isDesktop ? 4 : 3;
  const rowCount = 3;

  // Subtle width variation across columns while summing strictly to 100% of container width
  const rawWeights = Array.from({ length: colCount }, () =>
    randomize ? 0.98 + Math.random() * 0.04 : 1.0
  );
  const totalWeight = rawWeights.reduce((sum, w) => sum + w, 0);
  const colWidths = rawWeights.map((w) => Math.round((w / totalWeight) * width));

  // Ensure the final column lands flush with the right edge
  const sumExceptLast = colWidths.slice(0, -1).reduce((sum, w) => sum + w, 0);
  colWidths[colWidths.length - 1] = Math.max(width - sumExceptLast, 40);

  // Compute column left positions (starting flush at 0)
  const colLefts: number[] = [];
  let currLeft = 0;
  for (let c = 0; c < colCount; c += 1) {
    colLefts.push(currLeft);
    currLeft += colWidths[c];
  }

  // Row heights proportioned with an increase of 3-4vh total
  const avgColWidth = width / colCount;
  const vh = !randomize || typeof window === 'undefined' ? 900 : window.innerHeight;
  const extraRowHeight = Math.round((vh * 0.035) / rowCount);
  const baseRowHeight = Math.round(avgColWidth * 0.44) + extraRowHeight;
  const rowHeights = [baseRowHeight, baseRowHeight, baseRowHeight];

  const verticalPad = isDesktop ? 24 : 16;
  const rowTops = [
    verticalPad,
    verticalPad + rowHeights[0],
    verticalPad + rowHeights[0] + rowHeights[1],
  ];

  // STRICT CORNER-ONLY RULE:
  // 1. No consecutive boxes in any column: a column can only contain [0], [1], [2], or [0, 2] (never [0, 1] or [1, 2]).
  // 2. No consecutive boxes in any row: adjacent columns can never share the same row index,
  //    and every box must connect via corner (|r - p| === 1) to the adjacent column.
  //    On a 3-row grid, this means columns strictly alternate between [1] and {[0], [2], [0, 2]}.
  const outerChoices: readonly (readonly number[])[] = [[0], [2], [0, 2]];
  const tiles: PatternTile[] = [];

  // Deterministic corner-only pattern for initial SSR render
  const defaultColRows: readonly (readonly number[])[] = [[0, 2], [1], [0], [1]];

  let useMiddleRow = randomize ? Math.random() < 0.5 : false;

  for (let c = 0; c < colCount; c += 1) {
    const chosenRows = !randomize
      ? defaultColRows[c % defaultColRows.length]
      : useMiddleRow
        ? [1]
        : outerChoices[Math.floor(Math.random() * outerChoices.length)];

    useMiddleRow = !useMiddleRow;

    for (const r of chosenRows) {
      tiles.push({
        id: `tile-c${c}-r${r}-${colLefts[c]}-${rowTops[r]}`,
        left: colLefts[c],
        top: rowTops[r],
        width: colWidths[c],
        height: rowHeights[r],
      });
    }
  }

  const containerHeight = verticalPad * 2 + rowHeights[0] + rowHeights[1] + rowHeights[2];

  return {
    containerHeight,
    tiles,
  };
}

export function PatternDivider(): React.JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const tileRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [layout, setLayout] = useState<PatternLayout>(() => computePatternLayout(1440, false));
  const [isInView, setIsInView] = useState<boolean>(false);

  // Keep full width on window resize
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let lastWidth = el.clientWidth || window.innerWidth;
    setLayout(computePatternLayout(lastWidth));

    const handleResize = (): void => {
      const newWidth = el.clientWidth || window.innerWidth;
      if (newWidth > 0 && Math.abs(newWidth - lastWidth) > 2) {
        lastWidth = newWidth;
        setLayout(computePatternLayout(newWidth));
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

  // Re-randomize the rectangle layout every time the user scrolls into view
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
            const width = el.clientWidth || window.innerWidth || 1440;
            setLayout(computePatternLayout(width));
            setIsInView(true);
          } else {
            setIsInView(false);
          }
        });
      },
      { threshold: 0.15 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Animate the rectangles in a random one-by-one order via GSAP (fade in & fade out)
  useEffect(() => {
    const boxes = tileRefs.current
      .slice(0, layout.tiles.length)
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
          duration: 0.5,
          stagger: 0.08,
          ease: 'power3.out',
          overwrite: 'auto',
        }
      );
    } else {
      const shuffled = [...boxes];
      for (let i = shuffled.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }

      gsap.to(shuffled, {
        autoAlpha: 0,
        scale: 0.94,
        duration: 0.35,
        stagger: 0.04,
        ease: 'power2.in',
        overwrite: 'auto',
      });
    }

    return () => {
      gsap.killTweensOf(boxes);
    };
  }, [layout, isInView]);

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      style={{ height: `${layout.containerHeight}px` }}
      className="w-full overflow-hidden select-none bg-obsidian relative z-40"
    >
      {/* Full-Width Corner-Connected Muted Rectangles (Overlaps across the left margin) */}
      <div className="w-full h-full relative overflow-hidden">
        {layout.tiles.map((tile, idx) => (
          <div
            key={tile.id}
            ref={(node) => {
              tileRefs.current[idx] = node;
            }}
            style={{
              left: `${tile.left}px`,
              top: `${tile.top}px`,
              width: `${tile.width}px`,
              height: `${tile.height}px`,
            }}
            className="absolute bg-white/[0.035] border border-white/[0.04] opacity-0 will-change-transform"
          />
        ))}
      </div>
    </div>
  );
}

export function ProblemSection(): React.JSX.Element {
  const [activeIdx, setActiveIdx] = useState<number>(0);
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.IntersectionObserver === 'undefined') {
      return;
    }

    const observers: IntersectionObserver[] = [];

    itemRefs.current.forEach((el, index) => {
      if (!el) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setActiveIdx(index);
            }
          });
        },
        {
          rootMargin: '-20% 0px -20% 0px',
          threshold: 0.35,
        }
      );

      observer.observe(el);
      observers.push(observer);
    });

    return () => {
      observers.forEach((obs) => obs.disconnect());
    };
  }, []);

  return (
    <section id="problem" className="relative w-full flex flex-col">
      <div className="flex flex-col md:flex-row w-full">
        {/* Left Column (Sticky Sidebar aligned with 180px/220px vertical line) */}
        <div className="w-[180px] md:w-[220px] shrink-0 p-5 md:p-8 hidden md:block">
          <div className="sticky top-28">
            <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2">
              <span className="text-neon-blue">■</span>
              <span>The Problem</span>
            </h2>
            <div className="mt-4 text-[10px] text-slate-muted/50 tracking-widest font-mono">
              01 // THE PARADOX
            </div>
          </div>
        </div>

        {/* Right Column (Sequential Large Typography Statements) */}
        <div className="flex-1 p-5 md:pl-10 md:pr-12 pt-24 md:pt-36 pb-28 md:pb-44 max-w-5xl">
          {/* Mobile Section Title */}
          <div className="md:hidden mb-12">
            <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2">
              <span className="text-neon-blue">■</span>
              <span>The Problem</span>
            </h2>
          </div>

          <div className="space-y-28 md:space-y-40">
            {PROBLEM_STATEMENTS.map((item, index) => {
              const isActive = activeIdx === index;
              const isAdjacent = Math.abs(activeIdx - index) === 1;

              return (
                <div
                  key={item.id}
                  ref={(el) => {
                    itemRefs.current[index] = el;
                  }}
                  className={cn(
                    'transition-all duration-500 ease-out select-none cursor-default',
                    isActive
                      ? 'text-ivory font-medium opacity-100 translate-x-1'
                      : isAdjacent
                        ? 'text-slate-muted/70 opacity-60'
                        : 'text-slate-muted/30 opacity-30'
                  )}
                >
                  <p className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl leading-snug md:leading-[1.3] tracking-tight">
                    {item.text}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Atalanta-inspired Modular Geometric Pattern Divider */}
      <PatternDivider />
    </section>
  );
}

// ─── Section 3: Capabilities & Operational Domains ──────────────────────────

interface CapabilityCard {
  readonly id: string;
  readonly tag: string;
  readonly prefix: string;
  readonly title: string;
  readonly description: string;
  readonly bgImg?: string;
  readonly telemetry: string;
  readonly action?: 'map' | 'none';
}

const CAPABILITY_CARDS: readonly CapabilityCard[] = [
  {
    id: 'core-platform',
    tag: '01 // CORE PLATFORM',
    prefix: 'Hermes',
    title: 'The first spatial intelligence map.',
    description:
      'Real-time global event awareness mapped directly to physical space. Understand what is happening anywhere on Earth with verified spatial grounding and causal lineage.',
    telemetry: 'SYS // GEO-VERIFIED • MULTI-SOURCE CONSENSUS',
    action: 'map',
  },
  {
    id: 'geopolitical-security',
    tag: '02 // OPERATIONAL DOMAIN',
    prefix: 'Hermes',
    title: 'for Geopolitical Security.',
    description:
      'Track breaking border developments, military movements, and diplomatic shifts as they happen. Detect early signals of regional instability in physical geography before headlines catch up.',
    bgImg: satelliteImg,
    telemetry: 'SYS // RECON • GEOINT SRID 4326',
  },
  {
    id: 'energy-trade',
    tag: '03 // OPERATIONAL DOMAIN',
    prefix: 'Hermes',
    title: 'for Energy & Trade Corridors.',
    description:
      'Monitor maritime chokepoints, critical pipeline routes, and strategic ports. Observe how localized incidents immediately ripple through global shipping lanes and supply networks.',
    bgImg: mapChartImg,
    telemetry: 'SYS // MARITIME & ENERGY TRANSIT MONITOR',
  },
  {
    id: 'critical-infrastructure',
    tag: '04 // OPERATIONAL DOMAIN',
    prefix: 'Hermes',
    title: 'for Critical Infrastructure.',
    description:
      'Watch power grids, telecommunication corridors, and extreme environmental disruptions unfold. Trace the cascade of events across neighboring territories with spatial proximity.',
    bgImg: darkTextureImg,
    telemetry: 'SYS // GRID INTEGRITY & ENVIRONMENTAL TELEMETRY',
  },
] as const;

export function CapabilitiesSection(): React.JSX.Element {
  return (
    <section id="capabilities" className="relative w-full border-b border-border-subtle bg-obsidian">
      {/* Left Column (Sticky Sidebar Track aligned with 180px/220px vertical line) */}
      <div className="hidden md:block absolute top-0 bottom-0 left-0 w-[180px] md:w-[220px] z-30 pointer-events-none">
        <div className="sticky top-28 p-5 md:p-8 pointer-events-auto">
          <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2">
            <span className="text-neon-blue">■</span>
            <span>Capabilities</span>
          </h2>
          <div className="mt-4 text-[10px] text-slate-muted/50 tracking-widest font-mono">
            02 // OPERATIONAL DOMAINS
          </div>
        </div>
      </div>

      {/* Stacked Sticky Cards Container */}
      <div className="w-full relative">
        {CAPABILITY_CARDS.map((card) => (
          <div
            key={card.id}
            className="sticky top-0 min-h-screen w-full flex flex-col justify-between border-t border-white/[0.06] first:border-t-0 bg-obsidian overflow-hidden"
          >
            {/* Background Media Layer with Dark Gradient Tint */}
            {card.bgImg && (
              <div
                className="absolute inset-0 pointer-events-none select-none overflow-hidden"
                aria-hidden="true"
              >
                <img
                  src={card.bgImg}
                  alt={card.title}
                  className="w-full h-full object-cover opacity-20 filter grayscale contrast-125"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-r from-obsidian via-obsidian/85 to-obsidian/60" />
                <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-transparent to-obsidian/50" />
              </div>
            )}

            {/* Overlaid Card Content Container (Aligned with 180px/220px vertical line) */}
            <div className="relative z-10 w-full flex-1 flex flex-col justify-between pl-5 md:pl-[240px] pr-5 md:pr-12 lg:pr-16 pt-24 md:pt-32 pb-12 md:pb-16 max-w-7xl">
              {/* Content Header & Body */}
              <div>
                {/* Mobile Section Header */}
                <div className="md:hidden mb-4 flex items-center gap-2 text-xs uppercase tracking-widest text-ivory">
                  <span className="text-neon-blue">■</span>
                  <span>Capabilities</span>
                </div>

                {/* Card Domain Tag */}
                <div className="text-xs uppercase tracking-widest text-slate-muted/70 mb-8 md:mb-12 flex items-center gap-2">
                  <span className="text-neon-blue">■</span>
                  <span>{card.tag}</span>
                </div>

                {/* Two-Column Editorial Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-8 md:gap-14 lg:gap-16 items-start">
                  {/* Left Column: Monumental Headline */}
                  <div>
                    <h3 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-normal tracking-tight leading-[1.15]">
                      <span className="text-ivory font-bold block mb-2">{card.prefix}</span>
                      <span className="text-slate-muted/90">{card.title}</span>
                    </h3>
                  </div>

                  {/* Right Column: Narrative Copy & Optional CTA */}
                  <div className="space-y-8 max-w-xl">
                    <p className="text-base sm:text-lg md:text-xl text-slate-muted leading-relaxed">
                      {card.description}
                    </p>

                    {card.action === 'map' && (
                      <div className="pt-2">
                        <LaunchMapBtn className="px-5 py-2.5 text-xs tracking-widest" />
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Card Footer Telemetry Bar */}
              <div className="pt-12 mt-12 border-t border-white/[0.06] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-[10px] text-slate-muted/60 font-mono tracking-widest uppercase">
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-neon-blue inline-block animate-pulse" />
                  <span>{card.telemetry}</span>
                </div>
                <div className="text-slate-muted/40">[ {card.id.toUpperCase()} ]</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Send Message GSAP Button ────────────────────────────────────────────────

interface SendMessageBtnProps {
  readonly isSubmitting?: boolean;
  readonly disabled?: boolean;
  readonly className?: string;
}

export function SendMessageBtn({
  isSubmitting = false,
  disabled = false,
  className,
}: SendMessageBtnProps): React.JSX.Element {
  const labelRef = useRef<HTMLSpanElement>(null);
  const indicatorRef = useRef<HTMLSpanElement>(null);
  const arrow1Ref = useRef<HTMLSpanElement>(null);
  const arrow2Ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (indicatorRef.current && arrow2Ref.current) {
      gsap.set(indicatorRef.current, { x: -14, opacity: 0 });
      gsap.set(arrow2Ref.current, { x: -28, opacity: 0 });
    }
    return () => {
      gsap.killTweensOf([
        labelRef.current,
        indicatorRef.current,
        arrow1Ref.current,
        arrow2Ref.current,
      ]);
    };
  }, []);

  const handleMouseEnter = (): void => {
    if (isSubmitting || disabled) return;
    if (
      !labelRef.current ||
      !indicatorRef.current ||
      !arrow1Ref.current ||
      !arrow2Ref.current
    )
      return;

    gsap.killTweensOf([
      labelRef.current,
      indicatorRef.current,
      arrow1Ref.current,
      arrow2Ref.current,
    ]);

    // Text slides forward slightly
    gsap.to(labelRef.current, {
      x: 10,
      duration: 0.28,
      ease: 'power3.out',
    });

    // Tactical indicator glides in from left
    gsap.to(indicatorRef.current, {
      x: 0,
      opacity: 1,
      duration: 0.28,
      ease: 'power3.out',
    });

    // Projectile arrow: primary arrow shoots right
    gsap.to(arrow1Ref.current, {
      x: 28,
      opacity: 0,
      duration: 0.22,
      ease: 'power2.in',
    });

    // Incoming arrow sweeps into position from left
    gsap.fromTo(
      arrow2Ref.current,
      { x: -28, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.26, delay: 0.08, ease: 'power3.out' }
    );
  };

  const handleMouseLeave = (): void => {
    if (isSubmitting || disabled) return;
    if (
      !labelRef.current ||
      !indicatorRef.current ||
      !arrow1Ref.current ||
      !arrow2Ref.current
    )
      return;

    gsap.killTweensOf([
      labelRef.current,
      indicatorRef.current,
      arrow1Ref.current,
      arrow2Ref.current,
    ]);

    gsap.to(labelRef.current, {
      x: 0,
      duration: 0.24,
      ease: 'power2.inOut',
    });

    gsap.to(indicatorRef.current, {
      x: -14,
      opacity: 0,
      duration: 0.24,
      ease: 'power2.inOut',
    });

    gsap.to(arrow1Ref.current, {
      x: 0,
      opacity: 1,
      duration: 0.24,
      ease: 'power2.inOut',
    });

    gsap.to(arrow2Ref.current, {
      x: -28,
      opacity: 0,
      duration: 0.2,
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
        'group relative w-full bg-ivory text-black hover:bg-neon-blue hover:text-black transition-colors duration-200 py-4 px-6 text-xs uppercase tracking-widest font-bold font-mono flex items-center justify-between cursor-pointer rounded-none disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden',
        isSubmitting && 'bg-neon-blue text-black',
        className
      )}
      aria-label="Send message"
    >
      {/* Left side: text with slide indicator */}
      <div className="relative flex items-center">
        <span
          ref={indicatorRef}
          className="absolute -left-1 text-black font-black select-none pointer-events-none opacity-0 text-[10px]"
          aria-hidden="true"
        >
          ■
        </span>
        <span ref={labelRef} className="block tracking-widest select-none">
          {isSubmitting ? 'TRANSMITTING MESSAGE...' : 'SEND MESSAGE'}
        </span>
      </div>

      {/* Right side: projectile arrow cycle */}
      <div className="relative w-8 h-4 overflow-hidden flex items-center justify-end select-none pointer-events-none">
        <span ref={arrow1Ref} className="block text-base leading-none">
          →
        </span>
        <span
          ref={arrow2Ref}
          className="absolute right-0 block text-base leading-none opacity-0"
          aria-hidden="true"
        >
          →
        </span>
      </div>
    </button>
  );
}

// ─── Section 4: Contact ────────────────────────────────────────────────────

interface ContactFormData {
  readonly name: string;
  readonly email: string;
  readonly subject: string;
  readonly message: string;
}

export function ContactSection(): React.JSX.Element {
  const [formData, setFormData] = useState<ContactFormData>({
    name: '',
    email: '',
    subject: '',
    message: '',
  });
  const [status, setStatus] = useState<'idle' | 'submitting' | 'submitted'>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.email.trim() || !formData.message.trim()) {
      setErrorMsg('Name, email, and message are required.');
      return;
    }
    setErrorMsg(null);
    setStatus('submitting');
    setTimeout(() => {
      setStatus('submitted');
    }, 500);
  };

  const handleReset = (): void => {
    setFormData({ name: '', email: '', subject: '', message: '' });
    setStatus('idle');
    setErrorMsg(null);
  };

  return (
    <section id="contact" className="relative w-full border-b border-border-subtle bg-obsidian">
      {/* Anchor for backward compatibility if navigated from #access */}
      <span id="access" className="absolute -top-20" aria-hidden="true" />

      {/* Left Column (Sticky Sidebar Track aligned with 180px/220px vertical line) */}
      <div className="hidden md:block absolute top-0 bottom-0 left-0 w-[180px] md:w-[220px] z-30 pointer-events-none">
        <div className="sticky top-28 p-5 md:p-8 pointer-events-auto">
          <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2">
            <span className="text-neon-blue">■</span>
            <span>Contact</span>
          </h2>
          <div className="mt-4 text-[10px] text-slate-muted/50 tracking-widest font-mono">
            03 // GET IN TOUCH
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="relative z-10 w-full pl-5 md:pl-[240px] pr-5 md:pr-12 lg:pr-16 pt-20 md:pt-28 pb-20 md:pb-28 max-w-7xl">
        {/* Mobile Section Header */}
        <div className="md:hidden mb-8 flex items-center gap-2 text-xs uppercase tracking-widest text-ivory">
          <span className="text-neon-blue">■</span>
          <span>Contact</span>
        </div>

        {/* Section Tag */}
        <div className="text-xs uppercase tracking-widest text-slate-muted/70 mb-8 md:mb-12 flex items-center gap-2">
          <span className="text-neon-blue">■</span>
          <span>03 // CONTACT</span>
        </div>

        {/* Two-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
          {/* Left Column: Headline, Narrative & Security Badges */}
          <div className="space-y-8 max-w-xl">
            <h3 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight text-slate-muted leading-tight">
              Have questions or feedback?{' '}
              <span className="text-ivory font-bold block mt-2">
                Get in touch with me.
              </span>
            </h3>

            <p className="text-base sm:text-lg text-slate-muted leading-relaxed">
              Whether you're interested in spatial data architecture, collaboration on Hermes,
              research inquiries, or exploring the live maps—feel free to reach out. I read all
              messages directly.
            </p>

            {/* <div className="pt-2 space-y-3 text-xs font-mono text-slate-muted/80">
              <div className="flex items-center gap-3">
                <span className="text-neon-blue">■</span>
                <span>DIRECT CHANNEL // PERSONAL INBOX</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-neon-blue">■</span>
                <span>ENCRYPTED TRANSMISSION // TLS 1.3</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-neon-blue">■</span>
                <span>RESPONSE TIME // TYPICALLY 24-48H</span>
              </div>
            </div> */}
          </div>

          {/* Right Column: Brutalist Tactical Form */}
          <div className="w-full max-w-lg">
            {status === 'submitted' ? (
              <div className="border border-neon-blue/40 bg-neon-blue/5 p-6 md:p-8 space-y-5">
                <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-neon-blue">
                  <span className="w-2 h-2 bg-neon-blue inline-block animate-pulse" />
                  <span>200 OK // MESSAGE RECEIVED</span>
                </div>
                <p className="text-sm text-ivory leading-relaxed">
                  Thank you for reaching out! Your message has been received. I'll get back to you shortly at{' '}
                  <strong className="text-neon-blue font-mono">{formData.email}</strong>.
                </p>
                <div className="pt-2 text-[10px] text-slate-muted/60 font-mono tracking-widest uppercase">
                  STATUS // DELIVERED • ENCRYPTED TLS 1.3
                </div>
                <div className="pt-4 border-t border-neon-blue/20">
                  <button
                    type="button"
                    onClick={handleReset}
                    className="text-xs uppercase tracking-widest text-slate-muted hover:text-ivory transition-colors underline underline-offset-4 cursor-pointer"
                  >
                    Send another message →
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5" noValidate>
                <div>
                  <label
                    htmlFor="contact-name"
                    className="text-[10px] uppercase tracking-widest text-slate-muted/70 font-mono mb-2 block"
                  >
                    NAME *
                  </label>
                  <input
                    id="contact-name"
                    name="name"
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, name: e.target.value }))
                    }
                    placeholder="Your name"
                    className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="contact-email"
                    className="text-[10px] uppercase tracking-widest text-slate-muted/70 font-mono mb-2 block"
                  >
                    EMAIL ADDRESS *
                  </label>
                  <input
                    id="contact-email"
                    name="email"
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, email: e.target.value }))
                    }
                    placeholder="name@example.com"
                    className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="contact-subject"
                    className="text-[10px] uppercase tracking-widest text-slate-muted/70 font-mono mb-2 block"
                  >
                    SUBJECT
                  </label>
                  <input
                    id="contact-subject"
                    name="subject"
                    type="text"
                    value={formData.subject}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, subject: e.target.value }))
                    }
                    placeholder="e.g. Collaboration, Question, Feedback..."
                    className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="contact-message"
                    className="text-[10px] uppercase tracking-widest text-slate-muted/70 font-mono mb-2 block"
                  >
                    MESSAGE *
                  </label>
                  <textarea
                    id="contact-message"
                    name="message"
                    rows={4}
                    required
                    value={formData.message}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, message: e.target.value }))
                    }
                    placeholder="Write your message here..."
                    className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none resize-none"
                  />
                </div>

                {errorMsg && (
                  <div className="text-xs text-rose-400 font-mono tracking-wide">
                    [ ERROR // {errorMsg} ]
                  </div>
                )}

                <SendMessageBtn isSubmitting={status === 'submitting'} />
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

// Alias for backward compatibility
export const AccessSection = ContactSection;

// ─── Section 5: Editorial Brutalist Footer ───────────────────────────────────

export function Footer(): React.JSX.Element {
  return (
    <footer className="relative w-full border-t border-border-subtle bg-obsidian text-slate-muted font-mono z-40 overflow-hidden">
      {/* Background Modular Grid Pattern Tiles (Matching image_0abc5e.png colour & layout, flowing into upper footer) */}
      <div
        className="absolute inset-0 z-0 pointer-events-none select-none overflow-hidden"
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 1728 900"
          preserveAspectRatio="none"
          fill="none"
          className="w-full h-full"
        >
          <g fill="#ffffff" opacity="0.035">
            {/* Bottom-left box under the first letter */}
            <rect x="18" y="730" width="202" height="170" />
            {/* Lower-middle box stepping up to the right of the 220px line */}
            <rect x="220" y="560" width="195" height="170" />
            {/* Upper-middle tall box rising above the monumental wordmark */}
            <rect x="415" y="340" width="145" height="220" />
            {/* Top-left-center box flowing up into the Platform / Domains section */}
            <rect x="560" y="200" width="145" height="140" />
            {/* Wide middle box behind the center letters */}
            <rect x="560" y="560" width="285" height="170" />
            {/* Bottom-center box */}
            <rect x="845" y="730" width="215" height="170" />
            {/* Lower-middle right-of-center box */}
            <rect x="1060" y="560" width="190" height="170" />
            {/* Large upper-right box flowing up into the Intelligence / Protocol section */}
            <rect x="1250" y="250" width="290" height="310" />
            {/* Right-side tall box behind the final letter */}
            <rect x="1540" y="560" width="148" height="340" />
            {/* Top-right edge accent box */}
            <rect x="1688" y="160" width="40" height="90" />
          </g>
        </svg>
      </div>

      {/* Main Sitemap & Info Grid */}
      <div className="relative z-10 flex flex-col md:flex-row w-full">
        {/* Left Column (Aligned with 180px/220px desktop sidebar) */}
        <div className="hidden md:block w-[180px] md:w-[220px] shrink-0 p-5 md:p-8 border-r border-white/10">
          <div className="space-y-6">
            <div className="flex items-center gap-2 text-[10px] tracking-widest uppercase text-slate-muted/80">
              <span className="w-1.5 h-1.5 bg-emerald-400 inline-block animate-pulse" />
              <span>INFO</span>
            </div>
            <div className="text-[10px] tracking-wider text-slate-muted/50 leading-relaxed font-mono">
              HERMES
              <br />
              SPATIAL INTEL
              <br />
              SRID 4326
            </div>
            <div className="pt-4 flex flex-col gap-2 text-[11px] text-slate-muted/70 tracking-widest uppercase font-mono">
              <a
                href="https://github.com/paavann/hermes"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-ivory transition-colors flex items-center gap-1.5"
              >
                <span className="text-neon-blue">/</span>
                <span>GITHUB ↗</span>
              </a>
              <Link
                to="/map"
                className="hover:text-ivory transition-colors flex items-center gap-1.5"
              >
                <span className="text-neon-blue">/</span>
                <span>LIVE MAP ↗</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Right Column: 4-Column Sitemap & Bottom Telemetry */}
        <div className="flex-1 pl-5 md:pl-10 lg:pl-14 pr-5 md:pr-12 py-12 md:py-16">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-10">
            {/* 01 // PLATFORM */}
            <div className="space-y-4">
              <div className="text-xs font-mono uppercase tracking-widest text-ivory flex items-center gap-2">
                <span className="text-neon-blue">■</span>
                <span>Platform</span>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-muted font-mono">
                <li>
                  <Link to="/map" className="hover:text-ivory transition-colors">
                    Live Map
                  </Link>
                </li>
                <li>
                  <a href="#hero" className="hover:text-ivory transition-colors">
                    Orbital Observability
                  </a>
                </li>
                <li>
                  <a href="#problem" className="hover:text-ivory transition-colors">
                    The Problem
                  </a>
                </li>
                <li>
                  <a href="#capabilities" className="hover:text-ivory transition-colors">
                    Capabilities
                  </a>
                </li>
                <li>
                  <Link to="/login" className="hover:text-ivory transition-colors">
                    Operator Login
                  </Link>
                </li>
              </ul>
            </div>

            {/* 02 // DOMAINS */}
            <div className="space-y-4">
              <div className="text-xs font-mono uppercase tracking-widest text-ivory flex items-center gap-2">
                <span className="text-neon-blue">■</span>
                <span>Domains</span>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-muted font-mono">
                <li>
                  <a href="#capabilities" className="hover:text-ivory transition-colors">
                    Geopolitical
                  </a>
                </li>
                <li>
                  <a href="#capabilities" className="hover:text-ivory transition-colors">
                    Energy & Trade
                  </a>
                </li>
                <li>
                  <a href="#capabilities" className="hover:text-ivory transition-colors">
                    Infrastructure
                  </a>
                </li>
                <li>
                  <a href="#capabilities" className="hover:text-ivory transition-colors">
                    Environmental
                  </a>
                </li>
              </ul>
            </div>

            {/* 03 // INTELLIGENCE */}
            <div className="space-y-4">
              <div className="text-xs font-mono uppercase tracking-widest text-ivory flex items-center gap-2">
                <span className="text-neon-blue">■</span>
                <span>Intelligence</span>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-muted font-mono">
                <li className="text-slate-muted/70">Consensus Engine</li>
                <li className="text-slate-muted/70">Geocoding Shield</li>
                <li className="text-slate-muted/70">Causal Lineage</li>
                <li className="text-slate-muted/70">Credibility Tiers</li>
                <li className="text-slate-muted/70">Decay Model</li>
              </ul>
            </div>

            {/* 04 // PROTOCOL */}
            <div className="space-y-4">
              <div className="text-xs font-mono uppercase tracking-widest text-ivory flex items-center gap-2">
                <span className="text-neon-blue">■</span>
                <span>Protocol</span>
              </div>
              <ul className="space-y-2.5 text-xs text-slate-muted font-mono">
                <li>
                  <a href="#contact" className="hover:text-ivory transition-colors">
                    Contact
                  </a>
                </li>
                <li className="text-slate-muted/70">Privacy Protocol</li>
                <li className="text-slate-muted/70">Air-Gapped Ingestion</li>
                <li className="text-slate-muted/70">Security Audits</li>
                <li className="text-slate-muted/70">Terms of Clearance</li>
              </ul>
            </div>
          </div>

          {/* Sub-row Copyright & Top Jump */}
          <div className="pt-10 mt-12 border-t border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-slate-muted/60 font-mono">
            <div>© {new Date().getFullYear()} HERMES GEOINT INC. ALL RIGHTS RESERVED.</div>
            <div className="flex items-center gap-4">
              <Link to="/map" className="hover:text-ivory transition-colors">
                MAP
              </Link>
              <span className="text-white/10">/</span>
              <a href="#hero" className="hover:text-ivory transition-colors">
                TOP ↑
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Monumental Watermark: H with straight vertical stems + alternating up-down connected squares crossbar + 'ermes' */}
      <div className="relative z-10 bg-transparent w-full border-t border-white/[0.04] pt-14 md:pt-24 pb-2 md:pb-3 px-3 md:px-0 ml-10 flex items-end justify-center overflow-hidden select-none pointer-events-none">
        <div className="w-full flex items-end justify-center text-[#8F8C7C]">
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
      </div>
    </footer>
  );
}

// ─── Landing Page Shell ──────────────────────────────────────────────────────

export default function Landing(): React.JSX.Element {
  return (
    <div className="min-h-screen bg-obsidian text-slate-muted font-mono selection:bg-neon-blue/20 selection:text-neon-blue relative">
      {/* Atalanta-inspired Persistent Left Margin Line (Desktop) */}
      <div
        className="hidden md:block fixed top-0 bottom-0 left-[180px] md:left-[220px] w-px bg-white/10 z-30 pointer-events-none"
        aria-hidden="true"
      />

      {/* Fixed Minimalist Navigation Bar */}
      <Nav activeSection="home" />

      {/* Main Content Container */}
      <main id="main-content" className="pt-[62px]">
        {/* Section: Hero Frame */}
        <section id="hero" className="relative w-full">
          {/* Top Heading Area (aligned with the left line at 180px/220px) */}
          <div className="w-full pl-5 md:pl-[240px] pr-5 md:pr-8 pt-14 md:pt-20 pb-8 md:pb-16 max-w-6xl h-[65vh]">
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
        <ProblemSection />

        {/* Section: Capabilities (Sticky Stacking Cards) */}
        <CapabilitiesSection />

        {/* Section: Access */}
        <AccessSection />
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}