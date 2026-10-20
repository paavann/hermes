import type * as React from 'react';
import { cva } from 'class-variance-authority';
import type { VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

export const buttonVariants = cva(
  'inline-flex items-center justify-center font-mono font-bold uppercase transition-colors cursor-pointer select-none disabled:opacity-50 disabled:cursor-not-allowed rounded-none outline-none focus-visible:ring-1 focus-visible:ring-neon-blue',
  {
    variants: {
      variant: {
        default: 'bg-ivory text-black hover:bg-neon-blue hover:text-black',
        tactical: 'bg-ivory text-obsidian hover:bg-white',
        outline:
          'bg-black/60 border border-white/10 hover:border-neon-blue/60 hover:bg-white/[0.04] text-slate-muted hover:text-ivory',
        ghost: 'bg-transparent text-slate-muted hover:text-ivory hover:bg-white/5',
        link: 'text-slate-muted hover:text-neon-blue underline-offset-4 hover:underline p-0 h-auto font-normal',
      },
      size: {
        default: 'px-4 py-3 text-xs tracking-widest',
        sm: 'px-2.5 py-1 text-xs tracking-wider',
        md: 'px-4 py-2 text-xs tracking-wider',
        lg: 'px-6 py-4 text-xs tracking-widest',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  ref?: React.Ref<HTMLButtonElement>;
}

export function Button({
  className,
  variant,
  size,
  ref,
  type = 'button',
  ...props
}: ButtonProps): React.JSX.Element {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}
