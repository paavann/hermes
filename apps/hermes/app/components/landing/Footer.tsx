import type React from 'react';
import { Link } from 'react-router';

import { HermesWordmark, RollButton } from '@hermes/ui-components';

const FOOTER_COLUMNS: readonly {
  readonly index: string;
  readonly title: string;
  readonly items: readonly {
    readonly label: string;
    readonly href: string;
    readonly external?: boolean;
  }[];
}[] = [
  {
    index: '01',
    title: 'Platform',
    items: [
      { label: 'Live Map', href: '/map' },
      { label: 'Orbital Observability', href: '/#hero' },
      { label: 'The Problem', href: '/#problem' },
      { label: 'Capabilities', href: '/#capabilities' },
      { label: 'Operator Login', href: '/auth' },
    ],
  },
  {
    index: '02',
    title: 'Domains',
    items: [
      { label: 'Geopolitical', href: '/#capabilities' },
      { label: 'Energy & Trade', href: '/#capabilities' },
      { label: 'Infrastructure', href: '/#capabilities' },
      { label: 'Environmental', href: '/#capabilities' },
    ],
  },
  {
    index: '03',
    title: 'Intelligence',
    items: [
      { label: 'Vector Consensus', href: '/#capabilities' },
      { label: 'Geocoding Shield', href: '/#capabilities' },
      { label: 'Causal Lineage', href: '/#capabilities' },
      { label: 'Source Attribution', href: '/#capabilities' },
    ],
  },
  {
    index: '04',
    title: 'Protocol',
    items: [
      { label: 'Contact', href: '/#contact' },
      { label: 'Privacy Protocol', href: '/privacy' },
      {
        label: 'GitHub',
        href: 'https://github.com/paavann/hermes',
        external: true,
      },
    ],
  },
] as const;

export function Footer(): React.JSX.Element {
  return (
    <footer className="relative w-full overflow-hidden border-t border-border-subtle bg-obsidian font-mono text-slate-muted">
      <div
        className="pointer-events-none absolute inset-0 z-0 select-none overflow-hidden"
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 1728 900"
          preserveAspectRatio="none"
          fill="none"
          className="h-full w-full"
        >
          <g fill="#f1ede2" opacity="0.035">
            <rect x="18" y="730" width="202" height="170" />
            <rect x="220" y="560" width="195" height="170" />
            <rect x="415" y="340" width="145" height="220" />
            <rect x="560" y="200" width="145" height="140" />
            <rect x="560" y="560" width="285" height="170" />
            <rect x="845" y="730" width="215" height="170" />
            <rect x="1060" y="560" width="190" height="170" />
            <rect x="1250" y="250" width="290" height="310" />
            <rect x="1540" y="560" width="148" height="340" />
            <rect x="1688" y="160" width="40" height="90" />
          </g>
        </svg>
      </div>

      <div className="relative z-10 mx-auto flex w-full max-w-[1600px] flex-col">
        <div className="grid grid-cols-1 border-b border-border-subtle/70 md:grid-cols-[220px_minmax(0,1fr)]">
          <div className="hidden md:block">
            <div className="sticky top-24 border-r border-border-subtle/60 p-6 lg:p-8">
              <div className="space-y-5">
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-slate-muted/70">
                  <span className="h-1.5 w-1.5 animate-pulse bg-emerald-400" aria-hidden="true" />
                  <span>SYSTEM INFO</span>
                </div>
                <div className="space-y-1 text-[10px] uppercase leading-relaxed tracking-[0.14em] text-slate-muted/45">
                  <div className="flex items-center gap-2">
                    <span className="text-[8px] text-neon-blue">■</span>
                    <span>HERMES</span>
                  </div>
                  <div className="pl-3.5">SPATIAL INTEL</div>
                  <div className="pl-3.5">SRID 4326</div>
                </div>
                <div className="flex flex-col gap-2 border-t border-border-subtle pt-4 text-[10px] uppercase tracking-[0.16em] text-slate-muted/65">
                  <a
                    href="https://github.com/paavann/hermes"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-center gap-1.5 transition-colors hover:text-ivory"
                  >
                    <span className="text-neon-blue">/</span>
                    <span>GITHUB ↗</span>
                  </a>
                  <Link
                    to="/map"
                    className="group flex items-center gap-1.5 transition-colors hover:text-ivory"
                  >
                    <span className="text-neon-blue">/</span>
                    <span>LIVE MAP ↗</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <div className="flex-1 px-5 py-12 md:px-10 md:py-14 lg:px-14">
            <div className="flex flex-col gap-8 border-b border-border-subtle pb-12 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-neon-blue">
                  05 / LAUNCH
                </p>
                <p className="mt-3 max-w-xl font-display text-[clamp(2rem,4vw,3.75rem)] font-medium leading-[0.98] tracking-[-0.03em] text-ivory">
                  Observe the world in real time.
                </p>
              </div>
              <RollButton
                to="/map"
                label="LAUNCH MAP"
                hoverLabel="LAUNCH MAP ↗"
                ariaLabel="Launch the intelligence map"
                className="self-start px-5 py-2.5 text-[11px] tracking-[0.18em] md:self-auto"
              />
            </div>

            <div className="grid grid-cols-2 gap-8 pt-10 md:grid-cols-4 md:gap-10">
              {FOOTER_COLUMNS.map((column) => (
                <div key={column.index} className="space-y-4">
                  <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.18em] text-ivory">
                    <span className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
                      <span>{column.title}</span>
                    </span>
                    <span className="tabular-nums text-[9px] text-slate-muted/35">
                      {column.index}
                    </span>
                  </div>
                  <ul className="space-y-2.5 text-[11px] text-slate-muted">
                    {column.items.map((item) =>
                      item.external === true ? (
                        <li key={item.label}>
                          <a
                            href={item.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="transition-colors hover:text-ivory"
                          >
                            {item.label} ↗
                          </a>
                        </li>
                      ) : (
                        <li key={item.label}>
                          <a
                            href={item.href}
                            className="transition-colors hover:text-ivory"
                          >
                            {item.label}
                          </a>
                        </li>
                      ),
                    )}
                  </ul>
                </div>
              ))}
            </div>

            <div className="mt-12 flex flex-col items-start justify-between gap-4 border-t border-border-subtle pt-5 text-[10px] uppercase tracking-[0.14em] text-slate-muted/50 sm:flex-row sm:items-center">
              <div>
                © {new Date().getFullYear()} HERMES GEOINT INC. ALL RIGHTS
                RESERVED.
              </div>
              <div className="flex items-center gap-4">
                <Link to="/map" className="transition-colors hover:text-ivory">
                  MAP
                </Link>
                <span className="text-border-bright">/</span>
                <a href="#hero" className="transition-colors hover:text-ivory">
                  TOP ↑
                </a>
              </div>
            </div>
          </div>
        </div>

        <div className="flex w-full items-end justify-center overflow-hidden border-t border-border-subtle/60 px-0 pb-2 pt-12 select-none md:pb-3 md:pt-20">
          <div className="w-full text-bone/20">
            <HermesWordmark />
          </div>
        </div>
      </div>
    </footer>
  );
}
