import { useState, useEffect } from 'react';
import type React from 'react';
import { Link } from 'react-router';
import { Show, SignOutButton } from '@clerk/react-router';
import { cn, RollButton } from '@hermes/ui-components';

import type { NavItem } from './types';

export const NAV_ITEMS: readonly NavItem[] = [
  { id: 'home', label: 'Home', href: '#hero' },
  { id: 'problem', label: 'The Problem', href: '#problem' },
  { id: 'capabilities', label: 'Capabilities', href: '#capabilities' },
  { id: 'contact', label: 'Contact', href: '#contact' },
] as const;

export interface LaunchMapBtnProps {
  readonly className?: string;
}

export function LaunchMapBtn({ className }: LaunchMapBtnProps): React.JSX.Element {
  return (
    <RollButton
      to="/map"
      id="nav-launch-map"
      text1="LAUNCH MAP"
      text2="LAUNCH MAP ↗"
      ariaLabel="Launch the intelligence map"
      className={className}
    />
  );
}

export interface NavProps {
  readonly activeSection?: string;
}

export function Nav({ activeSection: controlledActiveSection }: NavProps): React.JSX.Element {
  const [scrolled, setScrolled] = useState<boolean>(false);
  const [detectedActiveSection, setDetectedActiveSection] = useState<string>('home');
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const activeSection = controlledActiveSection ?? detectedActiveSection;

  useEffect(() => {
    let ticking = false;

    const handleScroll = (): void => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          setScrolled(scrollY > 20);

          if (controlledActiveSection === undefined) {
            if (scrollY < 80) {
              setDetectedActiveSection('home');
              ticking = false;
              return;
            }

            const isBottom =
              window.innerHeight + scrollY >=
              document.documentElement.scrollHeight - 50;

            if (isBottom) {
              setDetectedActiveSection('contact');
              ticking = false;
              return;
            }

            const threshold = 180;
            let current = 'home';

            for (const item of NAV_ITEMS) {
              const targetId = item.href.replace('#', '');
              const el = document.getElementById(targetId);
              if (el) {
                const rect = el.getBoundingClientRect();
                if (rect.top <= threshold) {
                  current = item.id;
                }
              }
            }

            setDetectedActiveSection(current);
          }

          ticking = false;
        });
        ticking = true;
      }
    };

    handleScroll();

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [controlledActiveSection]);

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
                  onClick={() => {
                    if (controlledActiveSection === undefined) {
                      setDetectedActiveSection(item.id);
                    }
                  }}
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
            {/* Auth Status & Login / Logout Actions */}
            <Show when="signed-out">
              <Link
                to="/auth"
                className="text-xs uppercase tracking-wider text-slate-muted hover:text-ivory transition-colors"
              >
                LOGIN
              </Link>
            </Show>

            <Show when="signed-in">
              <SignOutButton redirectUrl="/auth">
                <button
                  type="button"
                  className="text-xs uppercase tracking-wider text-slate-muted hover:text-ivory transition-colors cursor-pointer"
                >
                  LOGOUT
                </button>
              </SignOutButton>
            </Show>

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
          {NAV_ITEMS.map((item) => {
            const isActive = activeSection === item.id;
            return (
              <a
                key={item.id}
                href={item.href}
                onClick={() => {
                  if (controlledActiveSection === undefined) {
                    setDetectedActiveSection(item.id);
                  }
                  setMobileMenuOpen(false);
                }}
                className={cn(
                  'flex items-center gap-2 py-2 text-xs uppercase tracking-wider border-b border-white/5 transition-colors',
                  isActive ? 'text-ivory font-medium' : 'text-slate-muted hover:text-ivory'
                )}
              >
                <span
                  className={cn(
                    'text-[9px] transition-colors',
                    isActive ? 'text-neon-blue' : 'text-slate-muted/60'
                  )}
                  aria-hidden="true"
                >
                  {isActive ? '■' : '/'}
                </span>
                <span>{item.label}</span>
              </a>
            );
          })}
          <Show when="signed-out">
            <Link
              to="/auth"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-2 py-2 text-xs uppercase tracking-wider text-slate-muted hover:text-ivory"
            >
              <span className="text-neon-blue text-[9px]">/</span>
              <span>LOGIN</span>
            </Link>
          </Show>
          <Show when="signed-in">
            <SignOutButton redirectUrl="/auth">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 py-2 text-xs uppercase tracking-wider text-slate-muted hover:text-ivory cursor-pointer w-full text-left"
              >
                <span className="text-neon-blue text-[9px]">/</span>
                <span>LOGOUT</span>
              </button>
            </SignOutButton>
          </Show>
        </div>
      )}
    </header>
  );
}
