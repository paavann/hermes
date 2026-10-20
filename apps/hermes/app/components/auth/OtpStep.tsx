import type React from 'react';
import { Label, TacticalActionBtn } from '@hermes/ui-components';
import type { AuthStatus } from './types';

export interface OtpStepProps {
  readonly email: string;
  readonly otpDigits: readonly string[];
  readonly otpInputRefs: React.RefObject<(HTMLInputElement | null)[]>;
  readonly isBusy: boolean;
  readonly status: AuthStatus;
  readonly resendCooldown: number;
  readonly errorMsg: string | null;
  readonly onOtpChange: (index: number, rawValue: string) => void;
  readonly onOtpKeyDown: (index: number, e: React.KeyboardEvent<HTMLInputElement>) => void;
  readonly onOtpPaste: (e: React.ClipboardEvent<HTMLInputElement>) => void;
  readonly onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  readonly onResend: () => void;
  readonly onChangeEmail: () => void;
  readonly onUsePassword: () => void;
}

export function OtpStep({
  email,
  otpDigits,
  otpInputRefs,
  isBusy,
  status,
  resendCooldown,
  errorMsg,
  onOtpChange,
  onOtpKeyDown,
  onOtpPaste,
  onSubmit,
  onResend,
  onChangeEmail,
  onUsePassword,
}: OtpStepProps): React.JSX.Element {
  return (
    <>
      <h1 className="text-2xl sm:text-3xl font-bold text-ivory tracking-tight text-center mb-2">
        Check your inbox
      </h1>
      <div className="text-xs text-slate-muted/80 text-center mb-7 flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
        <span>Enter the 6-digit code sent to</span>
        <span className="text-ivory font-medium">{email}</span>
        <button
          type="button"
          onClick={onChangeEmail}
          className="text-neon-blue hover:underline underline-offset-4 text-[11px] uppercase tracking-wider cursor-pointer"
        >
          [Change]
        </button>
      </div>

      <form onSubmit={onSubmit} className="w-full space-y-6" noValidate>
        {/* 6 Empty OTP Boxes */}
        <div>
          <Label className="text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2.5 block">
            Verification Code
          </Label>
          <div className="grid grid-cols-6 gap-2 sm:gap-2.5">
            {otpDigits.map((digit, idx) => (
              <input
                key={`otp-box-${idx}`}
                ref={(el) => {
                  if (otpInputRefs.current) {
                    otpInputRefs.current[idx] = el;
                  }
                }}
                type="text"
                inputMode="numeric"
                autoComplete={idx === 0 ? 'one-time-code' : 'off'}
                maxLength={6}
                disabled={isBusy}
                value={digit}
                onChange={(e) => onOtpChange(idx, e.target.value)}
                onKeyDown={(e) => onOtpKeyDown(idx, e)}
                onPaste={onOtpPaste}
                aria-label={`Digit ${idx + 1} of 6`}
                className="w-full aspect-square bg-black/60 border border-white/10 text-center text-lg sm:text-xl font-bold text-ivory focus:border-neon-blue focus:bg-white/3 focus:outline-none transition-colors font-mono rounded-none disabled:opacity-50"
              />
            ))}
          </div>
        </div>

        {errorMsg && (
          <div className="text-xs text-rose-400 font-mono tracking-wide text-center">
            {errorMsg}
          </div>
        )}

        <div className="pt-1">
          <TacticalActionBtn
            variant="roll"
            label="VERIFY & CONTINUE"
            loadingLabel="VERIFYING OTP..."
            isSubmitting={status === 'submitting'}
            disabled={isBusy}
          />
        </div>
      </form>

      {/* Resend OTP & Fallback Password Links */}
      <div className="w-full mt-6 flex items-center justify-between text-[11px] text-slate-muted/70 font-mono">
        <button
          type="button"
          disabled={resendCooldown > 0 || isBusy}
          onClick={onResend}
          className="hover:text-ivory transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {resendCooldown > 0
            ? `Resend code in ${resendCooldown}s`
            : 'Resend code'}
        </button>

        <button
          type="button"
          disabled={isBusy}
          onClick={onUsePassword}
          className="text-slate-muted/70 hover:text-neon-blue transition-colors underline underline-offset-4 cursor-pointer"
        >
          Use password instead
        </button>
      </div>
    </>
  );
}
