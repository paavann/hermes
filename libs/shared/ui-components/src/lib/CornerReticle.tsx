import type React from 'react';

import { cn } from './utils';

export interface CornerReticleProps {
  readonly className?: string;
  readonly tone?: 'cyan' | 'bone';
  readonly size?: 'sm' | 'md' | 'lg';
}

const SIZE_CLASSES: Record<NonNullable<CornerReticleProps['size']>, string> = {
  sm: 'h-2.5 w-2.5',
  md: 'h-4 w-4',
  lg: 'h-6 w-6',
};

const TONE_CLASSES: Record<NonNullable<CornerReticleProps['tone']>, string> = {
  cyan: 'border-neon-blue/80',
  bone: 'border-bone/40',
};

/**
 * Four L-shaped corner brackets used to frame HUD surfaces and media panels.
 * Purely decorative, so it is hidden from the accessibility tree.
 */
export function CornerReticle({
  className,
  tone = 'cyan',
  size = 'md',
}: CornerReticleProps): React.JSX.Element {
  const bracketClass = cn(
    'absolute border-0',
    SIZE_CLASSES[size],
    TONE_CLASSES[tone],
  );

  return (
    <div
      aria-hidden="true"
      className={cn('pointer-events-none absolute', className)}
    >
      <span className={cn(bracketClass, 'left-0 top-0 border-l border-t')} />
      <span className={cn(bracketClass, 'right-0 top-0 border-r border-t')} />
      <span className={cn(bracketClass, 'bottom-0 left-0 border-b border-l')} />
      <span className={cn(bracketClass, 'bottom-0 right-0 border-b border-r')} />
    </div>
  );
}
