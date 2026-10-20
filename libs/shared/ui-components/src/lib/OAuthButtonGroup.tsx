import type React from 'react';
import { cn } from './utils';

export type OAuthProviderId = 'google' | 'facebook' | 'x' | 'microsoft';

export interface OAuthProvider {
  readonly id: OAuthProviderId;
  readonly label: string;
  readonly icon: React.JSX.Element;
}

export const OAUTH_PROVIDERS: readonly OAuthProvider[] = [
  {
    id: 'google',
    label: 'Google',
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
        <path d="M21.35 11.1h-9.17v2.73h6.51c-.33 1.81-1.5 3.34-3.2 4.37v3.62h5.18c3.03-2.79 4.78-6.9 4.78-11.77 0-.8-.08-1.57-.23-2.31l.13.36z" />
        <path d="M12.18 22c4.32 0 7.95-1.43 10.6-3.88l-5.18-3.62c-1.43.96-3.26 1.53-5.42 1.53-4.17 0-7.7-2.81-8.96-6.59H-.13v3.73C2.51 18.41 7 22 12.18 22z" />
        <path d="M3.22 13.44c-.32-.96-.5-1.99-.5-3.05s.18-2.09.5-3.05V3.61H-.13C-1.2 5.75-1.82 8.16-1.82 10.39s.62 4.64 1.69 6.78l3.35-3.73z" />
        <path d="M12.18 4.75c2.35 0 4.46.81 6.12 2.4l4.59-4.59C20.12.98 16.5 0 12.18 0 7 0 2.51 3.59-.13 8.83l3.35 3.73c1.26-3.78 4.79-6.59 8.96-6.59z" />
      </svg>
    ),
  },
  {
    id: 'facebook',
    label: 'Facebook',
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
        <path d="M22.675 0H1.325C.593 0 0 .593 0 1.325v21.351C0 23.407.593 24 1.325 24H12.82v-9.294H9.692v-3.622h3.128V8.413c0-3.1 1.893-4.788 4.659-4.788 1.325 0 2.463.099 2.795.143v3.24l-1.918.001c-1.504 0-1.795.715-1.795 1.763v2.313h3.587l-.467 3.622h-3.12V24h6.116c.73 0 1.323-.593 1.323-1.325V1.325C24 .593 23.407 0 22.675 0z" />
      </svg>
    ),
  },
  {
    id: 'x',
    label: 'X / Twitter',
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
  },
  {
    id: 'microsoft',
    label: 'Microsoft',
    icon: (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
        <rect x="2" y="2" width="9.2" height="9.2" />
        <rect x="12.8" y="2" width="9.2" height="9.2" />
        <rect x="2" y="12.8" width="9.2" height="9.2" />
        <rect x="12.8" y="12.8" width="9.2" height="9.2" />
      </svg>
    ),
  },
] as const;

export interface OAuthButtonGroupProps {
  readonly activeProvider?: OAuthProviderId | null;
  readonly onSelect: (provider: OAuthProviderId) => void;
  readonly disabled?: boolean;
  readonly className?: string;
}

export function OAuthButtonGroup({
  activeProvider,
  onSelect,
  disabled = false,
  className,
}: OAuthButtonGroupProps): React.JSX.Element {
  return (
    <div className={cn('w-full grid grid-cols-2 gap-2.5', className)}>
      {OAUTH_PROVIDERS.map((provider) => {
        const isProviderLoading = activeProvider === provider.id;

        return (
          <button
            key={provider.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(provider.id)}
            className={cn(
              'group relative flex items-center justify-center gap-2.5 bg-black/60 border border-white/10 hover:border-neon-blue/60 hover:bg-white/[0.04] px-3 py-2.5 text-xs text-slate-muted hover:text-ivory transition-all duration-200 font-mono rounded-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
              isProviderLoading && 'border-neon-blue text-neon-blue bg-neon-blue/5'
            )}
            aria-label={`Continue with ${provider.label}`}
          >
            <span className="text-slate-muted group-hover:text-ivory transition-colors">
              {provider.icon}
            </span>
            <span className="tracking-wider uppercase text-[11px]">
              {isProviderLoading ? 'CONNECTING...' : provider.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
