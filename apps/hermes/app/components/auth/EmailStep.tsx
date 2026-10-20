import type React from 'react';
import {
  Input,
  Label,
  TacticalActionBtn,
  OAuthButtonGroup,
} from '@hermes/ui-components';
import type { OAuthProviderId } from '@hermes/ui-components';
import type { AuthStatus } from './types';

export interface EmailStepProps {
  readonly email: string;
  readonly isBusy: boolean;
  readonly status: AuthStatus;
  readonly activeOAuth: OAuthProviderId | null;
  readonly errorMsg: string | null;
  readonly onEmailChange: (value: string) => void;
  readonly onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly onSelectOAuth: (providerId: OAuthProviderId) => void;
}

export function EmailStep({
  email,
  isBusy,
  status,
  activeOAuth,
  errorMsg,
  onEmailChange,
  onSubmit,
  onSelectOAuth,
}: EmailStepProps): React.JSX.Element {
  return (
    <>
      <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-8">
        Welcome to Hermes
      </h1>

      <form onSubmit={onSubmit} className="w-full space-y-5" noValidate>
        <div>
          <Label
            htmlFor="auth-email"
            className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
          >
            Email
          </Label>
          <Input
            id="auth-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            disabled={isBusy}
            value={email}
            onChange={(e) => onEmailChange(e.target.value)}
            placeholder="operator@hermes.intel"
            className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
          />
        </div>

        {errorMsg && (
          <div className="text-xs text-rose-400 font-mono tracking-wide text-center">
            {errorMsg}
          </div>
        )}

        <div className="pt-1">
          <TacticalActionBtn
            variant="roll"
            label="CONTINUE"
            loadingLabel="DISPATCHING OTP..."
            isSubmitting={status === 'submitting'}
            disabled={isBusy}
          />
        </div>
      </form>

      {/* Tactical Divider */}
      <div
        className="w-full flex items-center gap-3 my-6 select-none"
        aria-hidden="true"
      >
        <div className="h-px flex-1 bg-white/10" />
        <span className="text-[10px] uppercase tracking-widest text-slate-muted/50 font-mono">
          OR CONTINUE WITH
        </span>
        <div className="h-px flex-1 bg-white/10" />
      </div>

      {/* 4 OAuth Options */}
      <OAuthButtonGroup
        activeProvider={activeOAuth}
        onSelect={onSelectOAuth}
        disabled={isBusy}
      />
    </>
  );
}
