import type React from 'react';
import { useState, useEffect } from 'react';
import { Link } from 'react-router';
import { Show, SignOutButton } from '@clerk/react-router';
import { cn, RollButton } from '@hermes/ui-components';

export function PrivacyNav(): React.JSX.Element {
  const [scrolled, setScrolled] = useState<boolean>(false);

  useEffect(() => {
    const handleScroll = (): void => {
      setScrolled(window.scrollY > 20);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      id="privacy-header"
      role="banner"
      className="fixed top-0 left-0 right-0 z-50 h-[62px] font-mono pointer-events-none"
    >
      <div className="w-full h-full flex items-center">
        {/* Left Column Brand */}
        <div
          className={cn(
            'w-[180px] md:w-[220px] shrink-0 h-full pl-5 md:pl-8 pr-4 flex items-center gap-3 pointer-events-auto transition-colors duration-250',
            scrolled ? 'bg-obsidian/90 backdrop-blur-md' : 'bg-transparent',
          )}
        >
          <Link
            to="/"
            aria-label="Hermes Home"
            className="font-bold tracking-[0.25em] text-sm text-ivory hover:text-white transition-colors"
          >
            HERMES
          </Link>
          <span className="hidden sm:inline-block text-xs text-slate-muted uppercase tracking-wider">
            Privacy Policy
          </span>
        </div>

        {/* Right Navigation & Tactical Actions */}
        <div
          className={cn(
            'flex-1 h-full pl-5 md:pl-8 pr-5 md:pr-8 flex items-center justify-between min-w-0 pointer-events-auto transition-colors duration-250',
            scrolled
              ? 'bg-obsidian/85 backdrop-blur-md border-b border-border-subtle shadow-[0_4px_30px_rgba(0,0,0,0.5)]'
              : 'bg-transparent',
          )}
        >
          {/* Quick Route Links */}
          <nav
            aria-label="Privacy navigation"
            className="hidden md:flex items-center gap-4 text-xs tracking-wider uppercase"
          >
            <Link
              to="/"
              className="text-slate-muted hover:text-ivory transition-colors flex items-center gap-1.5"
            >
              <span className="text-neon-blue">/</span>
              <span>HOME</span>
            </Link>
            <a
              href="https://github.com/paavann/hermes"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-muted hover:text-ivory transition-colors flex items-center gap-1.5"
            >
              <span className="text-neon-blue">/</span>
              <span>GITHUB ↗</span>
            </a>
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-5 ml-auto">
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

            <RollButton
              to="/map"
              id="privacy-launch-map"
              label="LAUNCH MAP"
              hoverLabel="LAUNCH MAP ↗"
              ariaLabel="Launch intelligence map"
              className="text-xs"
            />
          </div>
        </div>
      </div>
    </header>
  );
}
