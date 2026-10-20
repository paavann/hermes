import type React from 'react';
import { Input, Label, TacticalActionBtn } from '@hermes/ui-components';
import type { AuthStatus } from './types';

export interface PasswordStepProps {
  readonly email: string;
  readonly password: string;
  readonly isBusy: boolean;
  readonly status: AuthStatus;
  readonly errorMsg: string | null;
  readonly onPasswordChange: (value: string) => void;
  readonly onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly onChangeEmail: () => void;
  readonly onBackToOtp: () => void;
}

export function PasswordStep({
  email,
  password,
  isBusy,
  status,
  errorMsg,
  onPasswordChange,
  onSubmit,
  onChangeEmail,
  onBackToOtp,
}: PasswordStepProps): React.JSX.Element {
  return (
    <>
      <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-2">
        Enter your password
      </h1>
      <div className="text-xs text-slate-muted/80 text-center mb-7 flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
        <span>Signing in as</span>
        <span className="text-ivory font-medium">{email}</span>
        <button
          type="button"
          onClick={onChangeEmail}
          className="text-neon-blue hover:underline underline-offset-4 text-[11px] uppercase tracking-wider cursor-pointer"
        >
          [Change]
        </button>
      </div>

      <form onSubmit={onSubmit} className="w-full space-y-5" noValidate>
        <div>
          <Label
            htmlFor="fallback-password"
            className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
          >
            Password
          </Label>
          <Input
            id="fallback-password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            disabled={isBusy}
            value={password}
            onChange={(e) => onPasswordChange(e.target.value)}
            placeholder="••••••••••••"
            className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
          />
        </div>

        {errorMsg && (
          <div className="text-xs text-rose-400 font-mono tracking-wide">
            {errorMsg}
          </div>
        )}

        <div className="pt-1">
          <TacticalActionBtn
            variant="roll"
            label="CONTINUE"
            loadingLabel="AUTHENTICATING..."
            isSubmitting={status === 'submitting'}
            disabled={isBusy}
          />
        </div>
      </form>

      <div className="mt-6 text-center">
        <button
          type="button"
          onClick={onBackToOtp}
          className="text-[11px] text-slate-muted/70 hover:text-neon-blue transition-colors underline underline-offset-4 cursor-pointer font-mono"
        >
          ← Back to 6-digit OTP verification
        </button>
      </div>
    </>
  );
}
