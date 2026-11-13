import { useEffect, useRef, useState } from 'react';
import type React from 'react';
import gsap from 'gsap';
import ScrollTrigger from 'gsap/ScrollTrigger';

import { cn, RollButton } from '@hermes/ui-components';

import satelliteImg from '../../assets/satellite.jpg';
import mapChartImg from '../../assets/map-chart.jpg';
import darkTextureImg from '../../assets/dark-texture.jpg';

import { SectionHeading } from './SectionChrome';
import type { CapabilityCard } from './types';

if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
  gsap.registerPlugin(ScrollTrigger);
}

export const CAPABILITY_CARDS: readonly CapabilityCard[] = [
  {
    id: 'core-platform',
    domain: 'Core Platform',
    tag: '01 // CORE PLATFORM',
    prefix: 'Hermes',
    title: 'The first spatial intelligence map.',
    description:
      'Real-time global event awareness mapped directly to physical space. Understand what is happening anywhere on Earth with verified spatial grounding and causal lineage.',
    telemetry: 'SYS // GEO-VERIFIED • MULTI-SOURCE CONSENSUS',
    signals: [
      'Multi-source consensus',
      'Spatial grounding',
      'Causal event chains',
    ],
    action: 'map',
  },
  {
    id: 'geopolitical-security',
    domain: 'Geopolitical Security',
    tag: '02 // OPERATIONAL DOMAIN',
    prefix: 'Built for',
    title: 'Geopolitical Security.',
    description:
      'Track breaking border developments, military movements, and diplomatic shifts as they happen. Detect early signals of regional instability in physical geography before headlines catch up.',
    bgImg: satelliteImg,
    telemetry: 'SYS // RECON • GEOINT SRID 4326',
    signals: [
      'Border activity',
      'Military movement',
      'Diplomatic shifts',
    ],
  },
  {
    id: 'energy-trade',
    domain: 'Energy & Trade',
    tag: '03 // OPERATIONAL DOMAIN',
    prefix: 'Built for',
    title: 'Energy & Trade Corridors.',
    description:
      'Monitor maritime chokepoints, critical pipeline routes, and strategic ports. Observe how localized incidents immediately ripple through global shipping lanes and supply networks.',
    bgImg: mapChartImg,
    telemetry: 'SYS // MARITIME & ENERGY TRANSIT MONITOR',
    signals: [
      'Maritime chokepoints',
      'Pipeline corridors',
      'Strategic ports',
    ],
  },
  {
    id: 'critical-infrastructure',
    domain: 'Critical Infrastructure',
    tag: '04 // OPERATIONAL DOMAIN',
    prefix: 'Built for',
    title: 'Critical Infrastructure.',
    description:
      'Watch power grids, telecommunication corridors, and extreme environmental disruptions unfold. Trace the cascade of events across neighboring territories with spatial proximity.',
    bgImg: darkTextureImg,
    telemetry: 'SYS // GRID INTEGRITY & ENVIRONMENTAL TELEMETRY',
    signals: [
      'Power grids',
      'Telecom corridors',
      'Environmental disruption',
    ],
  },
] as const;

export function CapabilitiesSection(): React.JSX.Element {
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const mediaRefs = useRef<(HTMLDivElement | null)[]>([]);
  const overlayRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [activeIdx, setActiveIdx] = useState<number>(0);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }

    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;

    const ctx = gsap.context(() => {
      CAPABILITY_CARDS.forEach((_, idx) => {
        const card = cardRefs.current[idx];
        const nextCard = cardRefs.current[idx + 1];

        if (card) {
          ScrollTrigger.create({
            trigger: card,
            start: 'top 45%',
            end: 'bottom 45%',
            onToggle: (self) => {
              if (self.isActive) setActiveIdx(idx);
            },
          });
        }

        if (!nextCard || reduceMotion) return;

        const media = mediaRefs.current[idx];
        if (media) {
          gsap.fromTo(
            media,
            { scale: 1.05 },
            {
              scale: 1,
              ease: 'none',
              scrollTrigger: {
                trigger: nextCard,
                start: 'top bottom',
                end: 'top top',
                scrub: true,
              },
            },
          );
        }

        const overlay = overlayRefs.current[idx];
        if (overlay) {
          gsap.fromTo(
            overlay,
            { opacity: 0 },
            {
              opacity: 0.9,
              ease: 'none',
              scrollTrigger: {
                trigger: nextCard,
                start: 'top 50%',
                end: 'top top',
                scrub: true,
              },
            },
          );
        }
      });
    });

    return () => {
      ctx.revert();
    };
  }, []);

  return (
    <section
      id="capabilities"
      className="relative w-full border-b border-border-subtle bg-obsidian scroll-mt-16"
    >
      <div className="mx-auto grid w-full max-w-[1600px] grid-cols-1 md:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="hidden md:block">
          <div className="sticky top-24 space-y-3 p-6 lg:py-8 lg:pl-8 lg:pr-4">
            <SectionHeading
              index="03"
              label="Capabilities"
              meta="Operational domains"
            />

            <nav aria-label="Capability domains" className="mt-9 space-y-1">
              {CAPABILITY_CARDS.map((card, idx) => {
                const isActive = activeIdx === idx;

                return (
                  <a
                    key={card.id}
                    href={`#${card.id}`}
                    className={cn(
                      'flex items-center gap-3 border-l py-2.5 pl-3 text-[9px] uppercase tracking-[0.16em] transition-colors duration-150',
                      isActive
                        ? 'border-neon-blue bg-white/[0.025] text-ivory'
                        : 'border-border-subtle/50 text-slate-muted/50 hover:border-border-bright hover:text-bone',
                    )}
                  >
                    <span
                      className={cn(
                        'tabular-nums',
                        isActive ? 'text-neon-blue' : 'text-slate-muted/35',
                      )}
                    >
                      {String(idx + 1).padStart(2, '0')}
                    </span>
                    <span>{card.domain}</span>
                  </a>
                );
              })}
            </nav>

            <div className="mt-8 border-t border-border-subtle pt-4 text-[9px] uppercase tracking-[0.18em] text-slate-muted/40">
              {CAPABILITY_CARDS.length} domains / live map
            </div>
          </div>
        </aside>

        <div className="min-w-0 border-border-subtle/60 md:border-l">
          {CAPABILITY_CARDS.map((card, idx) => (
            <div
              key={card.id}
              id={card.id}
              ref={(el) => {
                cardRefs.current[idx] = el;
              }}
              style={{ zIndex: 10 + idx }}
              className="sticky top-0 flex min-h-dvh scroll-mt-16 flex-col overflow-hidden border-t border-border-subtle/70 bg-obsidian first:border-t-0"
            >
              <div
                className="absolute inset-0 bg-grid-hud opacity-25"
                aria-hidden="true"
              />

              {card.bgImg ? (
                <div
                  ref={(el) => {
                    mediaRefs.current[idx] = el;
                  }}
                  className="pointer-events-none absolute inset-0 select-none overflow-hidden will-change-transform"
                  aria-hidden="true"
                >
                  <img
                    src={card.bgImg}
                    alt=""
                    className="h-full w-full object-cover opacity-25 grayscale contrast-125"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-linear-to-r from-obsidian via-obsidian/85 to-obsidian/55" />
                  <div className="absolute inset-0 bg-linear-to-t from-obsidian via-transparent to-obsidian/45" />
                </div>
              ) : null}

              <div
                className="absolute inset-0 bg-obsidian opacity-0"
                ref={(el) => {
                  overlayRefs.current[idx] = el;
                }}
                aria-hidden="true"
              />

              <div
                className="pointer-events-none absolute -right-6 top-1/2 hidden -translate-y-1/2 select-none font-display text-[20rem] font-bold leading-none text-bone/[0.04] xl:block"
                aria-hidden="true"
              >
                {String(idx + 1).padStart(2, '0')}
              </div>

              <div className="relative z-10 flex flex-1 flex-col px-5 pb-8 pt-8 md:px-10 md:pb-10 md:pt-12 lg:px-14">
                <div className="md:hidden">
                  <SectionHeading index="03" label="Capabilities" />
                </div>

                <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-4 md:mt-0">
                  <div className="flex items-center gap-2.5 text-[10px] uppercase tracking-[0.2em] text-bone/70">
                    <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
                    <span>{card.tag}</span>
                  </div>
                  <div className="flex items-center gap-3 text-[9px] uppercase tracking-[0.18em] text-slate-muted/40">
                    <span className="tabular-nums">
                      {String(idx + 1).padStart(2, '0')} /{' '}
                      {String(CAPABILITY_CARDS.length).padStart(2, '0')}
                    </span>
                    <span className="h-1 w-6 bg-border-bright" aria-hidden="true" />
                  </div>
                </div>

                <div className="flex flex-1 flex-col justify-center py-10 md:py-14">
                  <div className="grid grid-cols-1 items-start gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
                    <h3 className="max-w-2xl font-display text-[clamp(2.4rem,4.8vw,4.4rem)] font-medium leading-[0.98] tracking-[-0.035em]">
                      <span className="mb-4 block font-mono text-[10px] font-normal uppercase tracking-[0.24em] text-neon-blue">
                        {card.prefix}
                      </span>
                      <span className="block text-ivory">{card.title}</span>
                    </h3>

                    <div className="max-w-xl space-y-8 lg:pt-2">
                      <p className="text-sm leading-relaxed text-slate-muted md:text-[15px]">
                        {card.description}
                      </p>

                      <div>
                        <div className="mb-2 flex items-center justify-between text-[9px] uppercase tracking-[0.18em] text-slate-muted/40">
                          <span>MONITORED SIGNALS</span>
                          <span className="tabular-nums">
                            {String(card.signals.length).padStart(2, '0')}
                          </span>
                        </div>
                        <div className="border-t border-border-subtle">
                          {card.signals.map((signal, signalIdx) => (
                            <div
                              key={signal}
                              className="flex items-center gap-3 border-b border-border-subtle/60 py-2.5 text-[10px] uppercase tracking-[0.12em] text-bone/70"
                            >
                              <span className="tabular-nums text-[9px] text-slate-muted/35">
                                {String(signalIdx + 1).padStart(2, '0')}
                              </span>
                              <span
                                className="h-1 w-1 bg-neon-blue/70"
                                aria-hidden="true"
                              />
                              <span>{signal}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {card.action === 'map' ? (
                        <RollButton
                          to="/map"
                          label="LAUNCH MAP"
                          hoverLabel="LAUNCH MAP ↗"
                          ariaLabel="Launch the intelligence map"
                          className="px-5 py-2.5 text-[11px] tracking-[0.18em]"
                        />
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col items-start justify-between gap-3 border-t border-border-subtle pt-5 text-[9px] uppercase tracking-[0.16em] text-slate-muted/45 sm:flex-row sm:items-center">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-1.5 w-1.5 animate-pulse bg-neon-blue"
                      aria-hidden="true"
                    />
                    <span>{card.telemetry}</span>
                  </div>
                  <span className="tabular-nums text-slate-muted/30">
                    [ {card.id.toUpperCase()} ]
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
