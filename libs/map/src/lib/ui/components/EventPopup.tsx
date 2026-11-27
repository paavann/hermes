import { useEffect, useState, useRef, useCallback } from 'react';
import {
  ArrowSquareOut,
  X,
} from '@phosphor-icons/react';

import { cn } from '@hermes/ui-components';

import { useMapStore } from '../../store/store';
import { useEventDetails } from '../../hooks/eventDetails';
import { relationshipTypeColor } from '../relationship-theme';

function getOutletTag(
  sourceName: string | null | undefined,
  title: string,
  domain: string,
): string {
  const name = sourceName?.toLowerCase() ?? '';
  if (name.includes('reuters')) return 'reuters';
  if (name.includes('associated press') || name.includes('ap wire')) return 'ap';
  if (name.includes('france-presse') || name.includes('afp')) return 'afp';
  if (name.includes('united press') || name.includes('upi')) return 'upi';
  if (name.includes('bbc')) return 'bbc';
  if (name.includes('new york times') || name.includes('nyt')) return 'nyt';
  if (name.includes('washington post') || name.includes('wapo')) return 'wapo';
  if (name.includes('guardian')) return 'guardian';
  if (name.includes('politico')) return 'politico';
  if (name.includes('al jazeera')) return 'aljazeera';
  if (name.includes('deutsche welle') || name.includes('dw')) return 'dw';
  if (name.includes('nhk')) return 'nhk';
  if (name.includes('cbc')) return 'cbc';
  if (name.includes('cnn')) return 'cnn';
  if (name.includes('npr')) return 'npr';
  if (name.includes('wsj') || name.includes('wall street journal')) return 'wsj';
  if (name.includes('pbs')) return 'pbs';
  if (name.includes('euronews')) return 'euronews';

  const titleLower = title.toLowerCase();
  if (titleLower.endsWith('- reuters') || titleLower.endsWith(' - reuters')) return 'reuters';
  if (titleLower.endsWith('- the associated press') || titleLower.endsWith('- ap news') || titleLower.endsWith('- ap')) return 'ap';
  if (titleLower.endsWith('- agence france-presse') || titleLower.endsWith('- afp')) return 'afp';
  if (titleLower.endsWith('- upi')) return 'upi';
  if (titleLower.endsWith('- bbc')) return 'bbc';

  if (domain.includes('reuters.com')) return 'reuters';
  if (domain.includes('apnews.com')) return 'ap';
  if (domain.includes('bbc.com') || domain.includes('bbc.co.uk')) return 'bbc';
  if (domain.includes('nytimes.com')) return 'nyt';
  if (domain.includes('washingtonpost.com')) return 'wapo';
  if (domain.includes('theguardian.com')) return 'guardian';

  if (sourceName) {
    return sourceName
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  }

  return domain.split('.')[0] || 'source';
}

function formatTimestamp(value: string | null | undefined): string | null {
  if (value === null || value === undefined || value.length === 0) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return `${new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  })
    .format(date)
    .toUpperCase()} UTC`;
}

export interface PopupInsets {
  readonly left?: number;
  readonly right?: number;
}

export interface EventPopupProps {
  readonly map: mapboxgl.Map | null;
  readonly onThreadOpen?: (threadId: string) => void;
  readonly popupInsets?: PopupInsets;
}

const VERIFICATION_LABEL: Record<string, string> = {
  CONFIRMED: 'CONFIRMED',
  CORROBORATED: 'CORROBORATED',
  SINGLE_SOURCE: 'SINGLE SOURCE',
  CONFLICTING: 'CONFLICTING',
  UNVERIFIED: 'UNVERIFIED',
};

const VERIFICATION_CLASS: Record<string, string> = {
  CONFIRMED: 'text-neon-blue',
  CORROBORATED: 'text-signal-teal-bright',
  SINGLE_SOURCE: 'text-signal-amber',
  CONFLICTING: 'text-danger-bright',
  UNVERIFIED: 'text-slate-muted',
};

export function EventPopup({
  map,
  onThreadOpen,
  popupInsets,
}: EventPopupProps) {
  const leftInset = Math.max(0, popupInsets?.left ?? 0);
  const rightInset = Math.max(0, popupInsets?.right ?? 0);
  const selectedEventId = useMapStore((s) => s.selectedEventId);
  const selectedEventLngLat = useMapStore((s) => s.selectedEventLngLat);
  const setSelectedEventId = useMapStore((s) => s.setSelectedEventId);
  const setTlMode = useMapStore((s) => s.setTlMode);
  const focusEvent = useMapStore((s) => s.focusEvent);

  const { data: event, isLoading, isError } = useEventDetails(selectedEventId);
  const [pos, setPos] = useState({ x: -9999, y: -9999 });
  const [scrambledSummary, setScrambledSummary] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);
  const actionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setIsClosing(false);
    setIsAnalyzing(false);
  }, [selectedEventId]);

  useEffect(() => {
    return () => {
      if (actionTimeoutRef.current) {
        clearTimeout(actionTimeoutRef.current);
      }
    };
  }, []);

  const handleAnalyze = useCallback(
    (e?: React.MouseEvent) => {
      e?.stopPropagation();
      if (isAnalyzing || !event) return;
      setIsAnalyzing(true);
      actionTimeoutRef.current = setTimeout(() => {
        setTlMode(true, event.id);
        setSelectedEventId(null);
        setIsAnalyzing(false);
      }, 90);
    },
    [isAnalyzing, event, setTlMode, setSelectedEventId],
  );

  const handleClose = useCallback(
    (e?: React.MouseEvent | React.KeyboardEvent) => {
      e?.stopPropagation();
      if (isClosing) return;
      setIsClosing(true);
      actionTimeoutRef.current = setTimeout(() => {
        setSelectedEventId(null);
        setIsClosing(false);
      }, 90);
    },
    [isClosing, setSelectedEventId],
  );

  useEffect(() => {
    if (!selectedEventId) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        handleClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedEventId, handleClose]);

  useEffect(() => {
    if (!map || !selectedEventLngLat) return;

    let animationFrameId: number;

    const updatePosition = () => {
      const p = map.project(selectedEventLngLat as [number, number]);
      let x = p.x;
      let y = p.y;

      if (popupRef.current) {
        const width = popupRef.current.offsetWidth;
        const height = popupRef.current.offsetHeight;
        const padding = 20;
        const minCenterX = leftInset + padding + width / 2;
        const maxCenterX = window.innerWidth - rightInset - padding - width / 2;
        if (minCenterX <= maxCenterX) {
          x = Math.max(minCenterX, Math.min(maxCenterX, x));
        } else {
          const fallbackMin = width / 2 + padding;
          const fallbackMax = window.innerWidth - width / 2 - padding;
          x =
            fallbackMin <= fallbackMax
              ? Math.max(fallbackMin, Math.min(fallbackMax, x))
              : window.innerWidth / 2;
        }
        y = Math.max(
          height / 2 + 68,
          Math.min(window.innerHeight - height / 2 - 42, y),
        );
      }

      setPos((prev) => {
        if (Math.abs(prev.x - x) < 0.5 && Math.abs(prev.y - y) < 0.5) {
          return prev;
        }
        return { x, y };
      });
      animationFrameId = requestAnimationFrame(updatePosition);
    };

    updatePosition();
    return () => cancelAnimationFrame(animationFrameId);
  }, [map, selectedEventLngLat, leftInset, rightInset]);

  useEffect(() => {
    if (event?.ai_summary === undefined || event.ai_summary.length === 0) {
      return;
    }

    const target = event.ai_summary;
    const reduceMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reduceMotion) {
      setScrambledSummary(target);
      return;
    }

    let iterations = 0;
    const maxIterations = 34;
    const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>[]{}';

    const interval = setInterval(() => {
      let newText = '';
      for (let i = 0; i < target.length; i++) {
        if (i < (iterations / maxIterations) * target.length) {
          newText += target[i];
        } else if (target[i] === ' ' || target[i] === '\n') {
          newText += target[i];
        } else {
          newText += CHARS[Math.floor(Math.random() * CHARS.length)];
        }
      }
      setScrambledSummary(newText);
      iterations++;

      if (iterations > maxIterations) {
        clearInterval(interval);
        setScrambledSummary(target);
      }
    }, 22);

    return () => clearInterval(interval);
  }, [event?.ai_summary]);

  if (!selectedEventId) return null;

  const importanceScore =
    event === undefined || event === null
      ? 0
      : Math.round(event.importance_score ?? 0);
  const sourceCount =
    event === undefined || event === null
      ? 0
      : (event.source_count ?? event.articles.length);
  const originCount = event?.independent_origin_count ?? 0;
  const verification = event?.verification_status ?? 'UNVERIFIED';
  const threadId = event?.thread_id ?? null;
  const firstReported = formatTimestamp(event?.first_reported_at);
  const lastUpdated = formatTimestamp(event?.last_updated_at);

  return (
    <div
      className="pointer-events-none absolute left-0 top-0 z-20"
      style={{
        transform: `translate(calc(${pos.x}px - 50%), calc(${pos.y}px - 50%))`,
      }}
    >
      <div
        ref={popupRef}
        onClick={(e) => e.stopPropagation()}
        role="region"
        aria-label="Event overview"
        className="pointer-events-auto flex max-h-[calc(100dvh-7rem)] w-[24rem] max-w-[calc(100vw-2rem)] flex-col border border-border-bright bg-obsidian font-mono"
      >
        <div className="flex items-start justify-between gap-3 border-b border-border-subtle bg-black px-3 py-2.5">
          <div className="flex min-w-0 flex-col gap-1">
            <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-neon-blue">
              <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
              OVERVIEW
            </span>
            {event && selectedEventLngLat ? (
              <span className="truncate text-[10px] tracking-wider text-slate-muted/65">
                {event.location_name ? `${event.location_name} • ` : ''}
                {selectedEventLngLat[1].toFixed(4)}°,{' '}
                {selectedEventLngLat[0].toFixed(4)}°
              </span>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close event overview"
            className={cn(
              'flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center border border-danger bg-danger text-black transition-colors duration-100 hover:border-danger-bright hover:bg-danger-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 active:scale-[0.98]',
              isClosing && 'animate-pop',
            )}
          >
            <X size={13} weight="bold" aria-hidden="true" />
          </button>
        </div>

        <div className="custom-scrollbar overflow-y-auto p-4">
          {isLoading ? (
            <p className="animate-pulse text-[10px] uppercase tracking-[0.2em] text-slate-muted/55">
              DECRYPTING PAYLOAD...
            </p>
          ) : null}
          {isError ? (
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-danger-bright">
              FAILED TO LOAD CONTENT. RETRY.
            </p>
          ) : null}

          {event ? (
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span
                  className="border px-2 py-1 text-[9px] font-bold uppercase tracking-[0.14em]"
                  style={{
                    color: event.category_color,
                    borderColor: event.category_color,
                  }}
                >
                  {event.category}
                </span>
              </div>

              <div>
                <h2 className="font-display text-[1.15rem] font-medium leading-tight tracking-[-0.02em] text-ivory">
                  {event.ai_headline}
                </h2>
                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] uppercase tracking-[0.14em] text-slate-muted/45">
                  {firstReported !== null ? <span>FIRST {firstReported}</span> : null}
                  {lastUpdated !== null ? <span>UPDATED {lastUpdated}</span> : null}
                  <span className="tabular-nums">{sourceCount} SOURCES</span>
                </div>
              </div>

              <div className="border-l-2 border-neon-blue bg-onyx p-3.5">
                <div className="mb-2 flex items-center justify-between text-[8px] uppercase tracking-[0.2em]">
                  <span className="text-neon-blue">AI SUMMARY</span>
                  <span className="text-slate-muted/30">GROUNDED</span>
                </div>
                <p className="whitespace-pre-wrap text-[11px] leading-relaxed text-bone/85">
                  {scrambledSummary}
                </p>
              </div>

              <div className="grid grid-cols-4 border border-border-subtle">
                <div className="border-r border-border-subtle px-2 py-2">
                  <div className="text-[8px] uppercase tracking-[0.14em] text-slate-muted/40">
                    IMPORTANCE
                  </div>
                  <div className="mt-1 tabular-nums text-sm font-bold text-signal-amber">
                    {importanceScore}
                  </div>
                </div>
                <div className="border-r border-border-subtle px-2 py-2">
                  <div className="text-[8px] uppercase tracking-[0.14em] text-slate-muted/40">
                    SOURCES
                  </div>
                  <div className="mt-1 tabular-nums text-sm font-bold text-neon-blue">
                    {sourceCount}
                  </div>
                </div>
                <div className="border-r border-border-subtle px-2 py-2">
                  <div className="text-[8px] uppercase tracking-[0.14em] text-slate-muted/40">
                    ORIGINS
                  </div>
                  <div className="mt-1 tabular-nums text-sm font-bold text-bone">
                    {originCount}
                  </div>
                </div>
                <div className="px-2 py-2">
                  <div className="text-[8px] uppercase tracking-[0.14em] text-slate-muted/40">
                    VERIFIED
                  </div>
                  <div
                    className={cn(
                      'mt-1 text-[10px] font-bold uppercase tracking-[0.06em]',
                      VERIFICATION_CLASS[verification] ?? 'text-slate-muted',
                    )}
                  >
                    {VERIFICATION_LABEL[verification] ?? verification}
                  </div>
                </div>
              </div>

              {threadId !== null && onThreadOpen !== undefined ? (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onThreadOpen(threadId);
                  }}
                  className="flex w-full cursor-pointer items-center justify-between border border-border-bright bg-onyx px-3 py-2 text-[10px] font-bold uppercase tracking-[0.18em] text-bone transition-colors duration-100 hover:border-neon-blue hover:text-neon-blue focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
                >
                  <span className="truncate">
                    STORY: {event.thread_name ?? 'OPEN THREAD'}
                  </span>
                  <span aria-hidden="true">→</span>
                </button>
              ) : null}

              <button
                type="button"
                onClick={handleAnalyze}
                className={cn(
                  'flex w-full cursor-pointer items-center justify-between border border-neon-blue bg-neon-blue px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.18em] text-black transition-colors duration-100 hover:border-ivory hover:bg-ivory focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 active:scale-[0.99]',
                  isAnalyzing && 'animate-pop',
                )}
              >
                <span>ANALYZE LINEAGE</span>
                <span aria-hidden="true">→</span>
              </button>

              {(event.actors?.length ?? 0) > 0 ? (
                <div>
                  <div className="mb-2 flex items-center justify-between text-[9px] uppercase tracking-[0.18em] text-slate-muted/50">
                    <span className="text-bone/80">ACTORS (WHO)</span>
                    <span className="tabular-nums">
                      {String(event.actors?.length ?? 0).padStart(2, '0')}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(event.actors ?? []).map((actor, idx) => (
                      <span
                        key={`${actor.name}-${actor.role}-${idx}`}
                        className="inline-flex items-center gap-1.5 border border-border-subtle bg-onyx px-2 py-1 text-[9px] uppercase tracking-[0.12em] text-bone/85"
                      >
                        <span className="font-bold text-ivory">{actor.name}</span>
                        <span className="text-slate-muted/55">{actor.role}</span>
                        {actor.country_code ? (
                          <span className="text-signal-amber/80">
                            {actor.country_code}
                          </span>
                        ) : null}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {(event.relationships?.length ?? 0) > 0 ? (
                <div>
                  <div className="mb-2 flex items-center justify-between text-[9px] uppercase tracking-[0.18em] text-slate-muted/50">
                    <span className="text-signal-amber">CONNECTED EVENTS</span>
                    <span className="tabular-nums">
                      {String(event.relationships?.length ?? 0).padStart(2, '0')}
                    </span>
                  </div>
                  <ul className="border-t border-border-subtle">
                    {(event.relationships ?? []).map((rel) => (
                      <li
                        key={rel.id}
                        className="border-b border-border-subtle/60"
                      >
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (
                              rel.related_longitude !== null &&
                              rel.related_latitude !== null
                            ) {
                              focusEvent(rel.related_event_id, [
                                rel.related_longitude,
                                rel.related_latitude,
                              ]);
                              return;
                            }
                            setSelectedEventId(rel.related_event_id, null);
                          }}
                          className="group flex w-full cursor-pointer flex-col gap-1 py-2.5 text-left transition-colors hover:bg-white/[0.02] focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
                        >
                          <div className="flex items-center justify-between gap-2 text-[9px] uppercase tracking-[0.14em]">
                            <span
                              className="flex items-center gap-1.5 font-bold"
                              style={{
                                color: relationshipTypeColor(
                                  rel.relationship_type,
                                ),
                              }}
                            >
                              <span
                                className="h-1.5 w-1.5 shrink-0"
                                style={{
                                  backgroundColor: relationshipTypeColor(
                                    rel.relationship_type,
                                  ),
                                }}
                                aria-hidden="true"
                              />
                              <span>
                                {rel.direction === 'OUTGOING'
                                  ? `${rel.relationship_type} →`
                                  : `← ${rel.relationship_type}`}
                              </span>
                            </span>
                            <span className="truncate text-slate-muted/55">
                              {rel.related_location_name ?? rel.related_category}
                            </span>
                          </div>
                          <span className="line-clamp-2 text-[10px] leading-snug text-bone/85 group-hover:text-ivory">
                            {rel.related_headline}
                          </span>
                          <span className="line-clamp-2 text-[9px] leading-relaxed text-slate-muted/55">
                            {rel.rationale}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div>
                <div className="mb-2 flex items-center justify-between text-[9px] uppercase tracking-[0.18em] text-slate-muted/50">
                  <span className="text-neon-blue">SOURCES</span>
                  <span className="tabular-nums">
                    {String(event.articles.length).padStart(2, '0')}
                  </span>
                </div>
                <ul className="border-t border-border-subtle">
                  {event.articles.map((article, idx) => {
                    let domain = '';
                    try {
                      domain = new URL(article.url).hostname.replace('www.', '');
                    } catch {
                      domain = 'source';
                    }

                    const outlet = getOutletTag(
                      article.source_name,
                      article.title,
                      domain,
                    );

                    return (
                      <li key={article.id} className="border-b border-border-subtle/60">
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group flex items-start gap-2.5 py-2.5 transition-colors hover:bg-white/[0.02] focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
                        >
                          <span className="shrink-0 tabular-nums text-[9px] text-slate-muted/30">
                            {String(idx + 1).padStart(2, '0')}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-[10px] leading-relaxed text-bone/75 group-hover:text-ivory">
                              {article.title}
                            </span>
                            <span className="mt-0.5 block text-[9px] uppercase tracking-[0.12em] text-slate-muted/45">
                              <span className="text-neon-blue/80">[{outlet}]</span>{' '}
                              {domain}
                            </span>
                          </span>
                          <ArrowSquareOut
                            size={11}
                            weight="bold"
                            aria-hidden="true"
                            className="mt-0.5 shrink-0 text-slate-muted/30 transition-colors group-hover:text-neon-blue"
                          />
                        </a>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
