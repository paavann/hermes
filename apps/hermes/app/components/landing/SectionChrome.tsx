import type React from 'react';

import { cn } from '@hermes/ui-components';

export interface SectionHeadingProps {
  readonly index: string;
  readonly label: string;
  readonly meta?: string;
  readonly className?: string;
}

/**
 * Shared section identity used by both the desktop rail and mobile headers.
 * Keeps index, label, and metadata typography consistent across the landing page.
 */
export function SectionHeading({
  index,
  label,
  meta,
  className,
}: SectionHeadingProps): React.JSX.Element {
  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center gap-2.5 whitespace-nowrap text-[11px] uppercase tracking-[0.22em] text-ivory">
        <span className="h-1.5 w-1.5 shrink-0 bg-neon-blue" aria-hidden="true" />
        <span className="font-medium">{label}</span>
        <span className="shrink-0 tabular-nums text-slate-muted/40">/ {index}</span>
      </div>
      {meta !== undefined ? (
        <p className="pl-4 text-[10px] uppercase tracking-[0.18em] text-slate-muted/50">
          {meta}
        </p>
      ) : null}
    </div>
  );
}

export interface SectionRailProps extends SectionHeadingProps {
  readonly children?: React.ReactNode;
}

/**
 * Fixed-width desktop rail that anchors landing sections to the vertical grid line.
 */
export function SectionRail({
  index,
  label,
  meta,
  className,
  children,
}: SectionRailProps): React.JSX.Element {
  return (
    <div className={cn('hidden w-[220px] shrink-0 md:block', className)}>
      <div className="sticky top-24 p-6 lg:py-8 lg:pl-8 lg:pr-4">
        <SectionHeading index={index} label={label} meta={meta} />
        {children}
      </div>
    </div>
  );
}

export interface SectionBodyProps {
  readonly children: React.ReactNode;
  readonly className?: string;
}

/**
 * Consistent content column beside a SectionRail. Owns the shared rhythm so
 * spacing never drifts between sections.
 */
export function SectionBody({
  children,
  className,
}: SectionBodyProps): React.JSX.Element {
  return (
    <div
      className={cn(
        'min-w-0 flex-1 border-border-subtle/60 px-5 py-12 md:border-l md:py-16 md:pl-10 md:pr-12 lg:pl-14',
        className,
      )}
    >
      {children}
    </div>
  );
}
