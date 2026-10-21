export type AuthMode = 'email' | 'login' | 'otp' | 'setup';

export type AuthStatus = 'idle' | 'submitting';

export interface SquareCell {
  readonly id: string;
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

export interface CheckerboardLayout {
  readonly cells: readonly SquareCell[];
}
