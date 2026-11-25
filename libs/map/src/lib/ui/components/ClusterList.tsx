import { X } from '@phosphor-icons/react';

import type { MapEventResponse } from '@hermes/util-types';

export interface ClusterListProps {
  readonly events: MapEventResponse[];
  readonly onSelect: (event: MapEventResponse) => void;
  readonly onClose: () => void;
  readonly hasRightPanel?: boolean;
}

export function ClusterList({
  events,
  onSelect,
  onClose,
  hasRightPanel = false,
}: ClusterListProps) {
  return (
    <div
      role="region"
      aria-label="Events in cluster"
      className={`pointer-events-auto absolute top-16 z-20 flex max-h-[60vh] w-[22rem] max-w-[calc(100vw-2rem)] flex-col border border-border-bright bg-obsidian font-mono ${
        hasRightPanel ? 'right-4 sm:right-[25rem]' : 'right-4'
      }`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-border-subtle bg-black px-3 py-2.5">
        <span className="flex min-w-0 items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-neon-blue">
          <span className="h-1.5 w-1.5 shrink-0 bg-neon-blue" aria-hidden="true" />
          <span className="truncate tabular-nums">
            CLUSTER // {events.length} EVENTS
          </span>
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close cluster list"
          className="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center border border-danger bg-danger text-black transition-colors duration-100 hover:border-danger-bright hover:bg-danger-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 active:scale-[0.98]"
        >
          <X size={13} weight="bold" aria-hidden="true" />
        </button>
      </div>

      <div className="custom-scrollbar overflow-y-auto">
        {events.map((event) => (
          <button
            key={event.id}
            type="button"
            onClick={() => onSelect(event)}
            className="group flex w-full cursor-pointer items-start gap-2.5 border-b border-border-subtle/60 px-3 py-2.5 text-left transition-colors duration-100 hover:bg-white/[0.02] focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-[-1px]"
          >
            <span
              className="mt-1 h-2 w-2 shrink-0"
              style={{ backgroundColor: event.category_color }}
              aria-hidden="true"
            />
            <span className="min-w-0 flex-1">
              <span className="line-clamp-2 block text-[11px] leading-snug text-bone/85 group-hover:text-ivory">
                {event.ai_headline}
              </span>
              <span className="mt-1 flex items-center gap-2 text-[9px] uppercase tracking-[0.12em] text-slate-muted/45">
                <span className="shrink-0">{event.category}</span>
                {event.location_name !== null ? (
                  <span className="truncate">{event.location_name}</span>
                ) : null}
                <span className="ml-auto shrink-0 tabular-nums text-signal-amber">
                  {Math.round(event.importance_score)}
                </span>
              </span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
