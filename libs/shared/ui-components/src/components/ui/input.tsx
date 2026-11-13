import type * as React from 'react';
import { cn } from '../../lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  ref?: React.Ref<HTMLInputElement>;
}

export function Input({
  className,
  type = 'text',
  ref,
  ...props
}: InputProps): React.JSX.Element {
  return (
    <input
      ref={ref}
      type={type}
      className={cn(
        'w-full bg-onyx border border-border-subtle px-3.5 py-3 text-sm text-ivory placeholder:text-slate-muted/35 transition-colors hover:border-border-bright focus:border-neon-blue focus:outline-none focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 font-mono rounded-none disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
      {...props}
    />
  );
}
