import type React from 'react';
import { Input, Label, TacticalActionBtn } from '@hermes/ui-components';
import type { AuthStatus } from './types';

export interface SetupStepProps {
  readonly email: string;
  readonly fullName: string;
  readonly password: string;
  readonly confirmPassword: string;
  readonly isBusy: boolean;
  readonly status: AuthStatus;
  readonly errorMsg: string | null;
  readonly onFullNameChange: (value: string) => void;
  readonly onPasswordChange: (value: string) => void;
  readonly onConfirmPasswordChange: (value: string) => void;
  readonly onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
}

export function SetupStep({
  email,
  fullName,
  password,
  confirmPassword,
  isBusy,
  status,
  errorMsg,
  onFullNameChange,
  onPasswordChange,
  onConfirmPasswordChange,
  onSubmit,
}: SetupStepProps): React.JSX.Element {
  return (
    <>
      <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-2">
        Complete your profile
      </h1>
      <p className="text-xs text-slate-muted/80 text-center mb-7">
        Set up your operator credentials for{' '}
        <span className="text-ivory font-medium">{email}</span>
      </p>

      <form onSubmit={onSubmit} className="w-full space-y-4" noValidate>
        {/* Full Name */}
        <div>
          <Label
            htmlFor="setup-name"
            className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
          >
            Full Name
          </Label>
          <Input
            id="setup-name"
            name="name"
            type="text"
            autoComplete="name"
            required
            disabled={isBusy}
            value={fullName}
            onChange={(e) => onFullNameChange(e.target.value)}
            placeholder="Elena Rostova"
            className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
          />
        </div>

        {/* Password */}
        <div>
          <Label
            htmlFor="setup-password"
            className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
          >
            Password
          </Label>
          <Input
            id="setup-password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            disabled={isBusy}
            value={password}
            onChange={(e) => onPasswordChange(e.target.value)}
            placeholder="••••••••••••"
            className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
          />
          <p className="mt-1.5 text-[11px] text-slate-muted/50 font-mono leading-relaxed">
            6+ characters, one number, and one capital letter
          </p>
        </div>

        {/* Confirm Password */}
        <div>
          <Label
            htmlFor="setup-confirm-password"
            className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block"
          >
            Confirm Password
          </Label>
          <Input
            id="setup-confirm-password"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            required
            disabled={isBusy}
            value={confirmPassword}
            onChange={(e) => onConfirmPasswordChange(e.target.value)}
            placeholder="••••••••••••"
            className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
          />
        </div>

        {errorMsg && (
          <div className="text-xs text-rose-400 font-mono tracking-wide text-center">
            {errorMsg}
          </div>
        )}

        <div className="pt-2">
          <TacticalActionBtn
            variant="roll"
            label="COMPLETE SETUP"
            loadingLabel="FINALIZING ACCOUNT..."
            isSubmitting={status === 'submitting'}
            disabled={isBusy}
          />
        </div>
      </form>
    </>
  );
}
