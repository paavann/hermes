import type React from 'react'
import { Link } from 'react-router'
import { HermesWordmark } from '@hermes/ui-components'

export function Footer(): React.JSX.Element {
  return (
    <footer className="relative w-full border-t border-border-subtle bg-obsidian text-slate-muted font-mono z-40 overflow-hidden">
      {/* Background Modular Grid Pattern Tiles */}
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
                  <Link
                    to="/map"
                    className="hover:text-ivory transition-colors"
                  >
                    Live Map
                  </Link>
                </li>
                <li>
                  <a
                    href="/#hero"
                    className="hover:text-ivory transition-colors"
                  >
                    Orbital Observability
                  </a>
                </li>
                <li>
                  <a
                    href="/#problem"
                    className="hover:text-ivory transition-colors"
                  >
                    The Problem
                  </a>
                </li>
                <li>
                  <a
                    href="/#capabilities"
                    className="hover:text-ivory transition-colors"
                  >
                    Capabilities
                  </a>
                </li>
                <li>
                  <Link
                    to="/auth"
                    className="hover:text-ivory transition-colors"
                  >
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
                  <a
                    href="/#capabilities"
                    className="hover:text-ivory transition-colors"
                  >
                    Geopolitical
                  </a>
                </li>
                <li>
                  <a
                    href="/#capabilities"
                    className="hover:text-ivory transition-colors"
                  >
                    Energy & Trade
                  </a>
                </li>
                <li>
                  <a
                    href="/#capabilities"
                    className="hover:text-ivory transition-colors"
                  >
                    Infrastructure
                  </a>
                </li>
                <li>
                  <a
                    href="/#capabilities"
                    className="hover:text-ivory transition-colors"
                  >
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
                  <a
                    href="/#contact"
                    className="hover:text-ivory transition-colors"
                  >
                    Contact
                  </a>
                </li>
                <li>
                  <Link
                    to="/privacy"
                    className="hover:text-ivory transition-colors"
                  >
                    Privacy Protocol
                  </Link>
                </li>
                <li className="text-slate-muted/70">Air-Gapped Ingestion</li>
                <li className="text-slate-muted/70">Security Audits</li>
                <li className="text-slate-muted/70">Terms of Clearance</li>
              </ul>
            </div>
          </div>

          {/* Sub-row Copyright & Top Jump */}
          <div className="pt-10 mt-12 border-t border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-slate-muted/60 font-mono">
            <div>
              © {new Date().getFullYear()} HERMES GEOINT INC. ALL RIGHTS
              RESERVED.
            </div>
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

      {/* Monumental Watermark */}
      <div className="relative z-10 bg-transparent w-full border-t border-white/[0.04] pt-14 md:pt-24 pb-2 md:pb-3 px-3 md:px-0 ml-10 flex items-end justify-center overflow-hidden select-none pointer-events-none">
        <div className="w-full flex items-end justify-center text-[#8F8C7C]">
          <HermesWordmark />
        </div>
      </div>
    </footer>
  )
}
