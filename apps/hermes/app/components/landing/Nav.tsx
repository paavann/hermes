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
      label="LAUNCH MAP"
      hoverLabel="LAUNCH MAP ↗"
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
      className="fixed left-0 right-0 top-0 z-50 h-[62px] font-mono"
    >
      <div className="flex h-full w-full items-center">
        <div
          className={cn(
            'flex h-full w-[150px] shrink-0 items-center border-r border-transparent pl-5 pr-4 transition-colors duration-150 sm:w-[180px] md:w-[220px] md:pl-8',
            scrolled
              ? 'border-border-subtle/60 bg-obsidian'
              : 'bg-transparent',
          )}
        >
          <Link
            to="/"
            aria-label="Hermes Home"
            className="group flex items-center gap-2.5 text-ivory transition-colors hover:text-white focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-4"
          >
            <span
              className="h-1.5 w-1.5 bg-neon-blue transition-transform duration-150 group-hover:scale-125"
              aria-hidden="true"
            />
            <span className="font-display text-[15px] font-semibold tracking-[0.2em]">
              HERMES
            </span>
            <span
              className="hidden text-[8px] font-normal tracking-[0.16em] text-neon-blue/60 sm:inline"
              aria-hidden="true"
            >
              GEO
            </span>
          </Link>
        </div>

        <div
          className={cn(
            'flex h-full flex-1 items-center justify-between gap-4 border-b border-transparent px-5 transition-colors duration-150 md:px-8',
            scrolled
              ? 'border-border-subtle/60 bg-obsidian'
              : 'bg-transparent',
          )}
        >
          <nav
            aria-label="Primary navigation"
            className="hidden items-center gap-1 md:flex"
          >
            {NAV_ITEMS.map((item, idx) => {
              const isActive = activeSection === item.id;

              return (
                <a
                  key={item.id}
                  href={item.href}
                  onClick={() => {
                    if (controlledActiveSection === undefined) {
                      setDetectedActiveSection(item.id);
                    }
                  }}
                  className={cn(
                    'group flex items-center gap-2 px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] transition-colors focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2',
                    isActive
                      ? 'text-ivory'
                      : 'text-slate-muted/65 hover:text-ivory',
                  )}
                >
                  <span
                    className={cn(
                      'tabular-nums text-[9px] transition-colors',
                      isActive
                        ? 'text-neon-blue'
                        : 'text-slate-muted/30 group-hover:text-signal-amber',
                    )}
                    aria-hidden="true"
                  >
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  <span>{item.label}</span>
                  <span
                    className={cn(
                      'h-1 w-1 transition-colors',
                      isActive
                        ? 'bg-neon-blue'
                        : 'bg-transparent group-hover:bg-signal-amber/70',
                    )}
                    aria-hidden="true"
                  />
                </a>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-3 md:gap-5">
            <Show when="signed-out">
              <Link
                to="/auth"
                className="hidden text-[10px] uppercase tracking-[0.18em] text-slate-muted/65 transition-colors hover:text-ivory focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-4 md:inline"
              >
                LOGIN
              </Link>
            </Show>

            <Show when="signed-in">
              <SignOutButton redirectUrl="/auth">
                <button
                  type="button"
                  className="hidden cursor-pointer text-[10px] uppercase tracking-[0.18em] text-slate-muted/65 transition-colors hover:text-ivory focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-4 md:block"
                >
                  LOGOUT
                </button>
              </SignOutButton>
            </Show>

            <LaunchMapBtn className="hidden sm:inline-flex" />

            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="flex items-center gap-1.5 border border-border-subtle bg-black px-2.5 py-1.5 text-[10px] uppercase tracking-[0.14em] text-slate-muted transition-colors hover:border-border-bright hover:text-ivory focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 md:hidden"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              <span className="text-neon-blue text-[8px]" aria-hidden="true">
                {mobileMenuOpen ? '■' : '/'}
              </span>
              <span>{mobileMenuOpen ? 'CLOSE' : 'MENU'}</span>
            </button>
          </div>
        </div>
      </div>

      {mobileMenuOpen ? (
        <div className="flex flex-col border-b border-border-subtle bg-obsidian px-5 py-3 md:hidden">
          {NAV_ITEMS.map((item, idx) => {
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
                  'flex items-center gap-3 border-b border-border-subtle/50 py-2.5 text-[10px] uppercase tracking-[0.16em] transition-colors',
                  isActive
                    ? 'text-ivory'
                    : 'text-slate-muted/65 hover:text-ivory',
                )}
              >
                <span
                  className={cn(
                    'tabular-nums text-[9px]',
                    isActive ? 'text-neon-blue' : 'text-slate-muted/30',
                  )}
                >
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <span>{item.label}</span>
                <span
                  className={cn(
                    'ml-auto h-1 w-1',
                    isActive ? 'bg-neon-blue' : 'bg-transparent',
                  )}
                  aria-hidden="true"
                />
              </a>
            );
          })}
          <Link
            to="/map"
            onClick={() => setMobileMenuOpen(false)}
            className="mt-3 flex items-center justify-between bg-ivory px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.18em] text-obsidian transition-colors hover:bg-neon-blue focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            <span>LAUNCH MAP</span>
            <span aria-hidden="true">↗</span>
          </Link>
          <Show when="signed-out">
            <Link
              to="/auth"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-3 py-2.5 text-[10px] uppercase tracking-[0.16em] text-slate-muted/65 hover:text-ivory"
            >
              <span className="tabular-nums text-[9px] text-slate-muted/30">05</span>
              <span>LOGIN</span>
            </Link>
          </Show>
          <Show when="signed-in">
            <SignOutButton redirectUrl="/auth">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="flex w-full cursor-pointer items-center gap-3 py-2.5 text-left text-[10px] uppercase tracking-[0.16em] text-slate-muted/65 hover:text-ivory"
              >
                <span className="tabular-nums text-[9px] text-slate-muted/30">05</span>
                <span>LOGOUT</span>
              </button>
            </SignOutButton>
          </Show>
        </div>
      ) : null}
    </header>
  );
}
