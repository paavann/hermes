import { useEffect, useRef } from 'react';
import type React from 'react';
import gsap from 'gsap';
import ScrollTrigger from 'gsap/ScrollTrigger';
import { RollButton } from '@hermes/ui-components';

import satelliteImg from '../../assets/satellite.jpg';
import mapChartImg from '../../assets/map-chart.jpg';
import darkTextureImg from '../../assets/dark-texture.jpg';

import type { CapabilityCard } from './types';

if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
  gsap.registerPlugin(ScrollTrigger);
}

export const CAPABILITY_CARDS: readonly CapabilityCard[] = [
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
];

export function CapabilitiesSection(): React.JSX.Element {
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const mediaRefs = useRef<(HTMLDivElement | null)[]>([]);
  const overlayRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;

    const ctx = gsap.context(() => {
      CAPABILITY_CARDS.forEach((_, idx) => {
        const nextCard = cardRefs.current[idx + 1];
        if (!nextCard) return;

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
            }
          );
        }

        const overlay = overlayRefs.current[idx];
        if (overlay) {
          gsap.fromTo(
            overlay,
            { opacity: 0 },
            {
              opacity: 0.85,
              ease: 'none',
              scrollTrigger: {
                trigger: nextCard,
                start: 'top 50%',
                end: 'top top',
                scrub: true,
              },
            }
          );
        }
      });
    });

    return () => {
      ctx.revert();
    };
  }, []);

  return (
    <section id="capabilities" className="relative w-full border-b border-border-subtle bg-obsidian scroll-mt-16">
      {/* Left Column (Sticky Sidebar Track aligned with 180px/220px vertical line) */}
      <div className="hidden md:block absolute top-0 bottom-0 left-0 w-[180px] md:w-[220px] z-30 pointer-events-none">
        <div className="sticky top-24 p-5 md:p-8 pointer-events-auto">
          <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2">
            <span className="text-neon-blue">■</span>
            <span>Capabilities</span>
          </h2>
          <div className="mt-4 text-[10px] text-slate-muted/50 tracking-widest font-mono">
            02 // OPERATIONAL DOMAINS
          </div>
        </div>
      </div>

      {/* Stacked Sticky Cards Container (Atalanta-inspired stack-on-scroll architecture) */}
      <div className="w-full relative pl-5 md:pl-5 pt-5 md:pt-5">
        {CAPABILITY_CARDS.map((card, idx) => (
          <div
            key={card.id}
            ref={(el) => {
              cardRefs.current[idx] = el;
            }}
            style={{ zIndex: 10 + idx }}
            className="sticky top-0 min-h-screen w-full flex flex-col justify-between border-t border-white/[0.06] first:border-t-0 bg-obsidian overflow-hidden"
          >
            {/* Background Media Layer with Dark Gradient Tint & Scroll Parallax */}
            {card.bgImg && (
              <div
                ref={(el) => {
                  mediaRefs.current[idx] = el;
                }}
                className="absolute inset-0 pointer-events-none select-none overflow-hidden will-change-transform"
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

            {/* Darkening Overlay during card-over-card stack transition */}
            <div
              ref={(el) => {
                overlayRefs.current[idx] = el;
              }}
              className="absolute inset-0 bg-obsidian opacity-0 pointer-events-none z-20 will-change-opacity"
              aria-hidden="true"
            />

            {/* Overlaid Card Content Container (Aligned with 180px/220px vertical line) */}
            <div className="relative z-10 w-full flex-1 flex flex-col justify-between pl-5 md:pl-[240px] pr-5 md:pr-12 lg:pr-16 pt-6 md:pt-10 pb-8 md:pb-12 max-w-7xl">
              {/* Content Header & Body */}
              <div>
                {/* Mobile Section Header */}
                <div className="md:hidden mb-4 flex items-center gap-2 text-xs uppercase tracking-widest text-ivory">
                  <span className="text-neon-blue">■</span>
                  <span>Capabilities</span>
                </div>

                {/* Card Domain Tag */}
                <div className="text-xs uppercase tracking-widest text-slate-muted/70 mb-5 md:mb-8 flex items-center gap-2">
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
                        <RollButton
                          to="/map"
                          label="LAUNCH MAP"
                          hoverLabel="LAUNCH MAP ↗"
                          ariaLabel="Launch the intelligence map"
                          className="px-5 py-2.5 text-xs tracking-widest"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Card Footer Telemetry Bar */}
              <div className="pt-8 mt-8 border-t border-white/[0.06] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-[10px] text-slate-muted/60 font-mono tracking-widest uppercase">
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
