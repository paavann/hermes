import { useEffect, useState, useRef, useCallback } from 'react';
import { useMapStore } from '../../store/store';
import { useEventDetails } from '../../hooks/eventDetails';

function getOutletTag(
  sourceName: string | null | undefined,
  title: string,
  domain: string,
): string {
  const name = sourceName?.toLowerCase() ?? '';
  if (name.includes('reuters')) return 'reuters';
  if (name.includes('associated press') || name.includes('ap wire'))
    return 'ap';
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
  if (name.includes('wsj') || name.includes('wall street journal'))
    return 'wsj';
  if (name.includes('pbs')) return 'pbs';
  if (name.includes('euronews')) return 'euronews';

  const titleLower = title.toLowerCase();
  if (titleLower.endsWith('- reuters') || titleLower.endsWith(' - reuters'))
    return 'reuters';
  if (
    titleLower.endsWith('- the associated press') ||
    titleLower.endsWith('- ap news') ||
    titleLower.endsWith('- ap')
  )
    return 'ap';
  if (
    titleLower.endsWith('- agence france-presse') ||
    titleLower.endsWith('- afp')
  )
    return 'afp';
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

export function EventPopup({ map }: { map: mapboxgl.Map | null }) {
  const selectedEventId = useMapStore((s) => s.selectedEventId);
  const selectedEventLngLat = useMapStore((s) => s.selectedEventLngLat);
  const setSelectedEventId = useMapStore((s) => s.setSelectedEventId);
  const setTlMode = useMapStore((s) => s.setTlMode);

  const { data: event, isLoading, isError } = useEventDetails(selectedEventId);
  const [pos, setPos] = useState({ x: -9999, y: -9999 });
  const [scrambledSummary, setScrambledSummary] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);
  const actionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset closing and analyzing states whenever the selected event changes
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

  // Keyboard accessibility: Escape key to dismiss the popup per modern web guidance
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

  // Track position flawlessly using requestAnimationFrame and Mapbox projection
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
        x = Math.max(
          width / 2 + padding,
          Math.min(window.innerWidth - width / 2 - padding, x),
        );
        y = Math.max(
          height / 2 + padding,
          Math.min(window.innerHeight - height / 2 - padding, y),
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
  }, [map, selectedEventLngLat]);

  // GSAP Scramble Text logic (Vanilla JS implementation for maximum safety without paid plugins)
  useEffect(() => {
    if (!event?.ai_summary) return;

    const target = event.ai_summary;
    let iterations = 0;
    const maxIterations = 50; // 50 frames at 30ms = 1.5 seconds
    const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>[]{}';

    const interval = setInterval(() => {
      let newText = '';
      for (let i = 0; i < target.length; i++) {
        // Reveal characters proportionally over the 50 iterations
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
    }, 30); // 30ms per frame

    return () => clearInterval(interval);
  }, [event?.ai_summary]);

  if (!selectedEventId) return null;

  return (
    <div
      className="absolute top-0 left-0 z-20 pointer-events-none"
      style={{
        transform: `translate(calc(${pos.x}px - 50%), calc(${pos.y}px - 50%))`,
      }}
    >
      <div
        ref={popupRef}
        onClick={(e) => e.stopPropagation()}
        role="region"
        aria-label="Event overview"
        className="pointer-events-auto bg-hud-bg/95 backdrop-blur-md border border-hud-border shadow-[0_0_20px_rgba(59,130,246,0.2)] flex flex-col w-96 max-h-[70vh] font-mono"
      >
        {/* Header */}
        <div className="flex justify-between items-start p-3 border-b border-hud-border bg-black/40 gap-2">
          <div className="flex flex-col gap-1 min-w-0">
            <span className="text-neon-blue font-bold tracking-[0.2em] text-xs uppercase">
              OVERVIEW
            </span>
            {event && selectedEventLngLat && (
              <span className="text-gray-400 text-[10px] tracking-wider truncate">
                {event.location_name ? `${event.location_name} • ` : ''}
                {selectedEventLngLat[1].toFixed(4)}°,{' '}
                {selectedEventLngLat[0].toFixed(4)}°
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close event overview"
            className={`cursor-pointer bg-[#ef4444] hover:bg-[#f87171] text-[#000000] font-mono font-bold text-[10px] tracking-wider px-2 py-0.5 uppercase transition-all duration-100 ease-out active:scale-[0.98] select-none shrink-0 ${
              isClosing ? 'animate-pop' : ''
            }`}
          >
            CLOSE
          </button>
        </div>

        {/* Content Area */}
        <div className="p-5 overflow-y-auto custom-scrollbar">
          {isLoading && (
            <p className="text-gray-500 animate-pulse text-xs tracking-widest">
              DECRYPTING PAYLOAD...
            </p>
          )}
          {isError && (
            <p className="text-red-500 font-bold tracking-widest">
              failed to load content. retry.
            </p>
          )}

          {event && (
            <div className="flex flex-col gap-5">
              {/* Badges */}
              <div className="flex gap-2">
                <span
                  className="px-2 py-1 text-[10px] font-bold tracking-[0.1em] border uppercase"
                  style={{
                    color: event.category_color,
                    borderColor: event.category_color,
                  }}
                >
                  {event.category}
                </span>
              </div>

              {/* Headline */}
              <h1 className="text-sm font-bold text-white uppercase tracking-wider">
                {event.ai_headline}
              </h1>

              {/* AI Summary */}
              <div className="bg-black/50 p-4 border-l-2 border-neon-blue flex flex-col gap-3">
                <p className="text-gray-300 text-xs leading-relaxed whitespace-pre-wrap">
                  {scrambledSummary}
                </p>
              </div>

              {/* Lineage Analyze Button */}
              <button
                type="button"
                onClick={handleAnalyze}
                className={`w-full py-2 bg-[#08929c] hover:bg-[#0aa5b1] text-[#000000] cursor-pointer text-xs font-mono font-bold tracking-widest uppercase transition-all duration-100 ease-out active:scale-[0.98] select-none ${
                  isAnalyzing ? 'animate-pop' : ''
                }`}
              >
                ANALYZE
              </button>

              {/* Verified Sources */}
              <div>
                <h3 className="text-neon-blue text-[10px] mb-3 tracking-[0.15em] uppercase">
                  Sources
                </h3>
                <ul className="flex flex-col gap-2">
                  {event.articles.map((article) => {
                    let domain = '';
                    try {
                      domain = new URL(article.url).hostname.replace(
                        'www.',
                        '',
                      );
                    } catch {
                      domain = 'source';
                    }

                    // Format link as domain/title per user request
                    const formattedTitle = article.title
                      .toLowerCase()
                      .replace(/[^a-z0-9]+/g, '-')
                      .replace(/(^-|-$)/g, '');

                    const outlet = getOutletTag(
                      article.source_name,
                      article.title,
                      domain,
                    );

                    return (
                      <li
                        key={article.id}
                        className="flex items-center gap-1.5 min-w-0"
                      >
                        <span className="text-neon-blue text-[8px] shrink-0">
                          ■
                        </span>
                        <span className="text-neon-blue text-[10px] font-mono shrink-0">
                          [{outlet}]
                        </span>
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-gray-400 hover:text-neon-blue text-[10px] hover:underline cursor-pointer truncate tracking-wider"
                        >
                          <span className="text-neon-blue">{domain}</span>/
                          {formattedTitle}
                        </a>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
