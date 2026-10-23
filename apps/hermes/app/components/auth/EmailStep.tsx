import type React from 'react';
import {
  Input,
  Label,
  TacticalActionBtn,
  OAuthButtonGroup,
} from '@hermes/ui-components';
import type { OAuthProviderId } from '@hermes/ui-components';
import type { AuthMode, AuthStatus } from './types';

export interface EmailStepProps {
  readonly mode?: AuthMode;
  readonly email: string;
  readonly password?: string;
  readonly isBusy: boolean;
  readonly status: AuthStatus;
  readonly activeOAuth: OAuthProviderId | null;
  readonly errorMsg: string | null;
  readonly onEmailChange: (value: string) => void;
  readonly onPasswordChange?: (value: string) => void;
  readonly onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly onSelectOAuth: (providerId: OAuthProviderId) => void;
  readonly onChangeEmail?: () => void;
  readonly onForgotPassword?: () => void;
}

export function EmailStep({
  mode = 'email',
  email,
  password = '',
  isBusy,
  status,
  activeOAuth,
  errorMsg,
  onEmailChange,
  onPasswordChange,
  onSubmit,
  onSelectOAuth,
  onChangeEmail,
  onForgotPassword,
}: EmailStepProps): React.JSX.Element {
  const isLoginMode = mode === 'login';

  return (
    <>
      <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-8">
        {isLoginMode ? 'Welcome Back!' : 'Welcome to Hermes!'}
      </h1>

      <form onSubmit={onSubmit} className="w-full space-y-5" noValidate>
        {/* Email Field */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label
              htmlFor="auth-email"
              className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono block"
            >
              Email
            </Label>
            {isLoginMode && onChangeEmail && (
              <button
                type="button"
                onClick={onChangeEmail}
                disabled={isBusy}
                className="text-neon-blue hover:underline underline-offset-4 text-[11px] uppercase tracking-wider cursor-pointer font-mono disabled:opacity-50"
              >
                [Change]
              </button>
            )}
          </div>
          <Input
            id="auth-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            disabled={isBusy || isLoginMode}
            value={email}
            onChange={(e) => onEmailChange(e.target.value)}
            placeholder="operator@hermes.intel"
            className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
          />
        </div>

        {/* Revealed Password Field in Login Mode */}
        {isLoginMode && (
          <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between mb-1">
              <Label
                htmlFor="auth-password"
                className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono block"
              >
                Password
              </Label>
              {onForgotPassword && (
                <button
                  type="button"
                  onClick={onForgotPassword}
                  disabled={isBusy}
                  className="text-neon-blue hover:underline underline-offset-4 text-[11px] uppercase tracking-wider cursor-pointer font-mono disabled:opacity-50"
                >
                  [Sign in with OTP]
                </button>
              )}
            </div>
            <Input
              id="auth-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              autoFocus
              disabled={isBusy}
              value={password}
              onChange={(e) => onPasswordChange?.(e.target.value)}
              placeholder="••••••••••••"
              className="w-full bg-black/60 border border-white/10 px-4 py-3 text-sm text-ivory placeholder:text-slate-muted/30 focus:border-neon-blue focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
            />
          </div>
        )}

        {errorMsg && (
          <div className="text-xs text-rose-400 font-mono tracking-wide text-center">
            {errorMsg}
          </div>
        )}

        <div className="pt-1">
          <TacticalActionBtn
            variant="roll"
            label={isLoginMode ? 'SIGN IN' : 'CONTINUE'}
            loadingLabel={isLoginMode ? 'SIGNING IN...' : 'CHECKING...'}
            isSubmitting={status === 'submitting'}
            disabled={isBusy}
          />
        </div>
      </form>

      {/* Tactical Divider & OAuth in initial email mode */}
      {!isLoginMode && (
        <>
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

          <OAuthButtonGroup
            activeProvider={activeOAuth}
            onSelect={onSelectOAuth}
            disabled={isBusy}
          />
        </>
      )}
    </>
  );
}
