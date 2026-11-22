import { X } from '@phosphor-icons/react';
import { cn } from '@hermes/ui-components';
import type { Map as MapboxMap } from 'mapbox-gl';

import { useMapStore } from '../../store/store';
import { useThreadDetails } from '../../hooks/useThreadDetails';

export interface StoryPanelProps {
  readonly map: MapboxMap | null;
  readonly threadId: string;
  readonly onClose: () => void;
}

const STATUS_CLASS: Record<string, string> = {
  ACTIVE: 'text-neon-blue',
  DORMANT: 'text-signal-amber',
  ENDED: 'text-slate-muted',
};

function formatDate(value: string | null): string {
  if (value === null) return '——';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '——';
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  })
    .format(date)
    .toUpperCase();
}

export function StoryPanel({
  map,
  threadId,
  onClose,
}: StoryPanelProps): React.JSX.Element {
  const { data: thread, isLoading, isError } = useThreadDetails(threadId);
  const setSelectedEventId = useMapStore((state) => state.setSelectedEventId);

  const handleEventClick = (
    eventId: string,
    latitude: number | null,
    longitude: number | null,
  ): void => {
    if (latitude === null || longitude === null) return;
    const lngLat: [number, number] = [longitude, latitude];
    map?.flyTo({
      center: lngLat,
      zoom: Math.max(map.getZoom(), 6),
      duration: 1200,
      essential: true,
    });
    setSelectedEventId(eventId, lngLat);
  };

  return (
    <aside
      aria-label="Story thread"
      className="pointer-events-auto absolute bottom-7 right-0 top-12 z-30 flex w-[24rem] max-w-[100vw] flex-col border-l border-border-bright bg-obsidian font-mono"
    >
      <div className="flex h-9 shrink-0 items-center justify-between border-b border-border-subtle bg-black px-3">
        <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-neon-blue">
          <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
          STORY THREAD
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close story thread"
          className="flex h-6 w-6 cursor-pointer items-center justify-center border border-border-bright text-bone transition-colors duration-100 hover:border-danger hover:bg-danger hover:text-black focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
        >
          <X size={12} weight="bold" aria-hidden="true" />
        </button>
      </div>

      <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto">
        {isLoading ? (
          <p className="p-4 text-[10px] uppercase tracking-[0.2em] text-slate-muted/55">
            LOADING THREAD...
          </p>
        ) : null}
        {isError ? (
          <p className="p-4 text-[10px] font-bold uppercase tracking-[0.18em] text-danger-bright">
            FAILED TO LOAD THREAD.
          </p>
        ) : null}

        {thread ? (
          <div className="flex flex-col gap-4 p-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="border border-border-bright px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.14em] text-bone">
                  {thread.kind}
                </span>
                <span
                  className={cn(
                    'text-[9px] font-bold uppercase tracking-[0.14em]',
                    STATUS_CLASS[thread.status] ?? 'text-slate-muted',
                  )}
                >
                  {thread.status}
                </span>
              </div>
              <h2 className="mt-2 font-display text-[1.05rem] font-medium leading-tight tracking-[-0.02em] text-ivory">
                {thread.name}
              </h2>
              {thread.description ? (
                <p className="mt-2 text-[11px] leading-relaxed text-bone/75">
                  {thread.description}
                </p>
              ) : null}
            </div>

            <div className="grid grid-cols-3 border border-border-subtle">
              <div className="border-r border-border-subtle px-2.5 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-muted/40">
                  EVENTS
                </div>
                <div className="mt-1 tabular-nums text-sm font-bold text-neon-blue">
                  {String(thread.event_count).padStart(2, '0')}
                </div>
              </div>
              <div className="border-r border-border-subtle px-2.5 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-muted/40">
                  IMPORTANCE
                </div>
                <div className="mt-1 tabular-nums text-sm font-bold text-signal-amber">
                  {Math.round(thread.importance)}
                </div>
              </div>
              <div className="px-2.5 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-muted/40">
                  LAST
                </div>
                <div className="mt-1 text-[10px] font-bold uppercase tracking-[0.08em] text-bone/80">
                  {formatDate(thread.last_event_at)}
                </div>
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between text-[9px] uppercase tracking-[0.18em] text-slate-muted/50">
                <span className="text-neon-blue">INCIDENTS</span>
                <span className="tabular-nums">
                  {String(thread.events.length).padStart(2, '0')}
                </span>
              </div>
              <ul className="border-t border-border-subtle">
                {thread.events.map((event) => (
                  <li
                    key={event.id}
                    className="border-b border-border-subtle/60"
                  >
                    <button
                      type="button"
                      onClick={() =>
                        handleEventClick(
                          event.id,
                          event.latitude,
                          event.longitude,
                        )
                      }
                      className="flex w-full cursor-pointer items-start gap-2.5 py-2.5 text-left transition-colors hover:bg-white/[0.02] focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
                    >
                      <span
                        className="mt-1 h-1.5 w-1.5 shrink-0"
                        style={{ backgroundColor: event.category_color }}
                        aria-hidden="true"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block text-[10px] leading-relaxed text-bone/80">
                          {event.ai_headline}
                        </span>
                        <span className="mt-0.5 block text-[9px] uppercase tracking-[0.12em] text-slate-muted/45">
                          {event.location_name ?? 'UNLOCATED'} ·{' '}
                          {formatDate(event.first_reported_at)}
                        </span>
                      </span>
                      <span className="shrink-0 tabular-nums text-[10px] text-signal-amber">
                        {Math.round(event.importance_score)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
