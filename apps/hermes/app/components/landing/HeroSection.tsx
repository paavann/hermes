import type React from 'react';

import { CornerReticle, RollButton } from '@hermes/ui-components';

import earthOrbitImg from '../../assets/earth-orbit.jpg';

interface HeroFact {
  readonly index: string;
  readonly label: string;
  readonly detail: string;
}

const HERO_FACTS: readonly HeroFact[] = [
  {
    index: '01',
    label: 'VECTOR CONSENSUS',
    detail: 'Independent sources, cross-checked',
  },
  {
    index: '02',
    label: 'CAUSAL LINEAGE',
    detail: 'Chronological context, reconstructed',
  },
  {
    index: '03',
    label: 'SPATIAL GROUNDING',
    detail: 'Every event tied to coordinates',
  },
] as const;

export function HeroSection(): React.JSX.Element {
  return (
    <section id="hero" className="relative w-full scroll-mt-16">
      <div className="mx-auto grid w-full max-w-[1600px] grid-cols-1 px-5 md:px-8 lg:grid-cols-[220px_minmax(0,1fr)] lg:px-0">
        <div className="hidden flex-col justify-between py-12 pl-8 pr-6 lg:flex">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-bone/60">
              <span className="text-neon-blue">01</span>
              <span className="h-px w-6 bg-border-bright" />
              <span>OVERVIEW</span>
            </div>
            <p className="max-w-[9rem] text-[10px] uppercase leading-relaxed tracking-[0.18em] text-slate-muted/45">
              Live geospatial intelligence
            </p>
          </div>

          <div className="space-y-3">
            <span className="block h-px w-10 bg-neon-blue/60" />
            <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.2em] text-slate-muted/50">
              <span className="h-1.5 w-1.5 animate-pulse bg-neon-blue" aria-hidden="true" />
              <span>FEED ACTIVE</span>
            </div>
          </div>
        </div>

        <div className="min-w-0 border-border-subtle/60 py-10 lg:border-l lg:py-12 lg:pl-10 lg:pr-10">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2.5 text-[10px] uppercase tracking-[0.22em] text-bone/70">
              <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
              <span>Hermes Intelligence</span>
            </div>
            <div className="flex items-center gap-3 text-[9px] uppercase tracking-[0.2em] text-slate-muted/45">
              <span className="flex items-center gap-1.5">
                <span className="h-1 w-1 bg-signal-amber" aria-hidden="true" />
                <span>REAL-TIME FEED</span>
              </span>
              <span className="h-3 w-px bg-border-subtle" aria-hidden="true" />
              <span className="tabular-nums">SRID 4326</span>
            </div>
          </div>

          <h1 className="mt-9 max-w-5xl font-display text-[clamp(2.6rem,5.4vw,5.15rem)] font-medium leading-[0.97] tracking-[-0.035em] text-ivory">
            Global event observability for{' '}
            <span className="text-bone/75">
              the world&apos;s most{' '}
              <span className="text-neon-blue">critical</span> decisions.
            </span>
          </h1>

          <div className="mt-10 grid grid-cols-1 gap-8 border-t border-border-subtle pt-7 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            <p className="max-w-2xl text-sm leading-relaxed text-slate-muted md:text-[15px]">
              I built Hermes to change how you experience the world. Instead of
              losing the signal inside endless feeds and headlines, observe
              critical global events as they unfold — with spatial context,
              verified sourcing, and quiet clarity.
            </p>

            <div className="flex flex-wrap items-center gap-4">
              <RollButton
                to="/map"
                label="LAUNCH MAP"
                hoverLabel="LAUNCH MAP ↗"
                ariaLabel="Launch the intelligence map"
                className="px-5 py-2.5 text-[11px] tracking-[0.18em]"
              />
              <a
                href="#capabilities"
                className="group inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-slate-muted transition-colors hover:text-ivory focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-4"
              >
                <span>EXPLORE CAPABILITIES</span>
                <span
                  aria-hidden="true"
                  className="text-neon-blue transition-transform duration-150 group-hover:translate-y-0.5"
                >
                  ↓
                </span>
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1600px] px-5 pb-14 md:px-8 md:pb-20">
        <div className="group relative overflow-hidden border border-border-subtle bg-onyx">
          <div className="relative h-[clamp(320px,50vh,560px)] overflow-hidden">
            <img
              src={earthOrbitImg}
              alt="Earth seen from orbit"
              className="h-full w-full object-cover object-top opacity-80 grayscale-[0.25] transition-opacity duration-500 group-hover:opacity-90"
              loading="eager"
            />
            <div
              className="absolute inset-0 bg-linear-to-r from-obsidian/85 via-obsidian/20 to-transparent"
              aria-hidden="true"
            />
            <div
              className="absolute inset-0 bg-linear-to-t from-obsidian via-transparent to-obsidian/35"
              aria-hidden="true"
            />
            <div
              className="absolute inset-0 bg-scanline opacity-40"
              aria-hidden="true"
            />
            <CornerReticle className="inset-3" tone="cyan" size="md" />

            <div className="absolute left-4 top-4 flex items-center gap-2 text-[9px] uppercase tracking-[0.22em] text-bone/70 md:left-6 md:top-6">
              <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
              <span>ORBITAL OBSERVABILITY</span>
            </div>

            <div className="absolute bottom-4 left-4 right-4 flex flex-wrap items-end justify-between gap-3 md:bottom-6 md:left-6 md:right-6">
              <div className="max-w-xs border-l border-neon-blue/60 pl-3">
                <p className="text-[9px] uppercase tracking-[0.2em] text-slate-muted/60">
                  GLOBAL EVENT SURFACE
                </p>
                <p className="mt-1 font-display text-sm font-medium tracking-tight text-ivory md:text-base">
                  The world, observed in context.
                </p>
              </div>
              <div className="flex items-center gap-2 border border-border-subtle bg-black px-2.5 py-1.5 text-[9px] uppercase tracking-[0.18em] text-slate-muted">
                <span className="h-1 w-1 bg-signal-amber" aria-hidden="true" />
                <span>SRID 4326 / MERCATOR</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 border-t border-border-subtle sm:grid-cols-3">
            {HERO_FACTS.map((fact, idx) => (
              <div
                key={fact.index}
                className={`flex flex-col gap-1.5 p-4 md:p-5 ${
                  idx < HERO_FACTS.length - 1
                    ? 'border-b border-border-subtle sm:border-b-0 sm:border-r'
                    : ''
                }`}
              >
                <div className="flex items-center justify-between text-[9px] tabular-nums tracking-[0.2em] text-slate-muted/45">
                  <span>{fact.index}</span>
                  <span className="h-1 w-1 bg-neon-blue/70" aria-hidden="true" />
                </div>
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-ivory">
                  {fact.label}
                </p>
                <p className="text-[10px] leading-relaxed text-slate-muted/65">
                  {fact.detail}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
