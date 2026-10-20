import type React from 'react';
import { cn } from './utils';

export interface HermesWordmarkProps extends React.ComponentProps<'svg'> {
  className?: string;
}

export function HermesWordmark({
  className,
  ...props
}: HermesWordmarkProps): React.JSX.Element {
  return (
    <svg
      viewBox="45 96 1370 284"
      fill="currentColor"
      className={cn('w-full h-auto block', className)}
      aria-label="Hermes"
      role="img"
      {...props}
    >
      {/* First Letter H: Left straight vertical stem */}
      <rect x="45" y="100" width="38" height="275" />

      {/* Horizontal Crossbar: Alternating up-down-up-down-up squares with touching edges */}
      <rect x="83" y="218" width="31" height="36" />
      <rect x="114" y="240" width="31" height="36" />
      <rect x="145" y="218" width="31" height="36" />
      <rect x="176" y="240" width="31" height="36" />
      <rect x="207" y="218" width="29" height="36" />

      {/* Right vertical stem */}
      <rect x="236" y="100" width="38" height="275" />

      {/* Lowercase 'ermes' in JetBrains Mono typography */}
      <text
        x="295"
        y="375"
        fontFamily="'JetBrains Mono', 'Fira Code', monospace"
        fontSize="375"
        fontWeight="700"
        letterSpacing="-0.04em"
      >
        ermes
      </text>
    </svg>
  );
}
