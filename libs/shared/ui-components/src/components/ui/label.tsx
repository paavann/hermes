import type * as React from 'react';
import { cn } from '../../lib/utils';

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  ref?: React.Ref<HTMLLabelElement>;
}

export function Label({
  className,
  ref,
  ...props
}: LabelProps): React.JSX.Element {
  return (
    <label
      ref={ref}
      className={cn(
        'text-[10px] md:text-[11px] uppercase tracking-widest text-slate-muted/80 font-mono mb-2 block select-none',
        className
      )}
      {...props}
    />
  );
}
