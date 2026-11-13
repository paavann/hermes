import { useEffect, useState } from 'react';

import type { MapEventResponse } from '@hermes/util-types';
import { cn } from '@hermes/ui-components';

import { useMapStore } from '../../store/store';

export interface MapHudProps {
  readonly events: readonly MapEventResponse[];
  readonly isFetching: boolean;
}

function formatDegrees(
  value: number | null,
  positive: string,
  negative: string,
): string {
  if (value === null || Number.isNaN(value)) {
    return '——';
  }
  const direction = value >= 0 ? positive : negative;
  return `${Math.abs(value).toFixed(2)}°${direction}`;
}

function useUtcClock(): string {
  const [clock, setClock] = useState<string>('--:--:-- UTC');

  useEffect(() => {
    const update = (): void => {
      setClock(`${new Date().toISOString().substring(11, 19)} UTC`);
    };

    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  return clock;
}

/**
 * Persistent command chrome for the live map: identity, viewport telemetry,
 * feed status, and a factual category legend derived from loaded events.
 */
export function MapHud({ events, isFetching }: MapHudProps): React.JSX.Element {
  const viewport = useMapStore((state) => state.viewport);
  const citedCount = useMapStore((state) => state.citedEvents.length);
  const clock = useUtcClock();

  const centerLat =
    viewport === null ? null : (viewport.north + viewport.south) / 2;
  const centerLon =
    viewport === null ? null : (viewport.east + viewport.west) / 2;
  const centerLng =
    centerLon !== null && centerLon > 180 ? centerLon - 360 : centerLon;

  const categories = Array.from(
    new Map(events.map((event) => [event.category, event.category_color])),
  ).slice(0, 4);

  return (
    <>
      <header className="pointer-events-auto absolute inset-x-0 top-0 z-40 flex h-12 items-center justify-between gap-3 border-b border-border-subtle bg-black px-3 font-mono md:px-4">
        <div className="flex min-w-0 items-center gap-3">
          <a
            href="/"
            aria-label="Hermes home"
            className="group flex items-center gap-2.5 transition-colors focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-4"
          >
            <span className="h-1.5 w-1.5 bg-neon-blue transition-transform duration-150 group-hover:scale-125" aria-hidden="true" />
            <span className="font-display text-[13px] font-semibold tracking-[0.18em] text-ivory">
              HERMES
            </span>
            <span className="hidden text-[8px] tracking-[0.16em] text-neon-blue/60 sm:inline">
              GEOINT
            </span>
          </a>
          <span className="h-4 w-px bg-border-subtle" aria-hidden="true" />
          <span className="hidden items-center gap-2 text-[9px] uppercase tracking-[0.18em] text-slate-muted/55 sm:flex">
            <span className="h-1 w-1 bg-signal-amber" aria-hidden="true" />
            <span>LIVE MAP</span>
          </span>
        </div>

        <div className="hidden items-center gap-5 text-[9px] uppercase tracking-[0.16em] text-slate-muted/55 md:flex">
          <span className="flex items-center gap-1.5">
            <span className="text-slate-muted/35">LAT</span>
            <span className="tabular-nums text-bone/85">
              {formatDegrees(centerLat, 'N', 'S')}
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="text-slate-muted/35">LON</span>
            <span className="tabular-nums text-bone/85">
              {formatDegrees(centerLng, 'E', 'W')}
            </span>
          </span>
          <span className="h-3 w-px bg-border-subtle" aria-hidden="true" />
          <span className="flex items-center gap-1.5">
            <span className="text-slate-muted/35">EVENTS</span>
            <span className="tabular-nums text-neon-blue">
              {String(events.length).padStart(3, '0')}
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="text-slate-muted/35">CITED</span>
            <span className="tabular-nums text-signal-amber">
              {String(citedCount).padStart(2, '0')}
            </span>
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <span className="flex items-center gap-1.5 text-[9px] uppercase tracking-[0.18em] text-slate-muted/60">
            <span
              className={cn(
                'h-1.5 w-1.5',
                isFetching ? 'animate-pulse bg-signal-amber' : 'bg-emerald-400',
              )}
              aria-hidden="true"
            />
            <span>{isFetching ? 'SYNCING' : 'LIVE'}</span>
          </span>
          <span className="h-3 w-px bg-border-subtle" aria-hidden="true" />
          <span className="tabular-nums text-[10px] tracking-[0.12em] text-bone/80">
            {clock}
          </span>
        </div>
      </header>

      <footer className="pointer-events-auto absolute inset-x-0 bottom-0 z-40 flex h-7 items-center justify-between gap-3 border-t border-border-subtle bg-black px-3 font-mono text-[9px] uppercase tracking-[0.14em] text-slate-muted/50">
        <div className="flex min-w-0 items-center gap-3 overflow-hidden">
          <span className="shrink-0 text-slate-muted/35">SRID 4326</span>
          <span className="h-2.5 w-px shrink-0 bg-border-subtle" aria-hidden="true" />
          <span className="hidden shrink-0 sm:inline">MERCATOR</span>
          <span className="h-2.5 w-px shrink-0 bg-border-subtle sm:hidden" aria-hidden="true" />
          {categories.length > 0 ? (
            <div className="flex min-w-0 items-center gap-3 overflow-hidden">
              {categories.map(([category, color]) => (
                <span
                  key={category}
                  className="flex shrink-0 items-center gap-1.5"
                  title={category}
                >
                  <span
                    className="h-1.5 w-1.5"
                    style={{ backgroundColor: color }}
                    aria-hidden="true"
                  />
                  <span className="truncate text-slate-muted/55">{category}</span>
                </span>
              ))}
            </div>
          ) : (
            <span className="flex items-center gap-1.5 text-signal-amber/70">
              <span className="h-1.5 w-1.5 bg-signal-amber" aria-hidden="true" />
              <span>AWAITING FEED</span>
            </span>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2 tabular-nums">
          <span className="hidden text-slate-muted/35 sm:inline">VIEWPORT</span>
          <span className="text-bone/70">
            {formatDegrees(centerLat, 'N', 'S')} /{' '}
            {formatDegrees(centerLng, 'E', 'W')}
          </span>
        </div>
      </footer>
    </>
  );
}
