import { useEffect, useState } from 'react';
import { useMapStore } from '../../store/store';
import { useEventDetails } from '../../hooks/eventDetails';

export function EventPopup({ map }: { map: mapboxgl.Map | null }) {
  const selectedEventId = useMapStore(s => s.selectedEventId);
  const selectedEventLngLat = useMapStore(s => s.selectedEventLngLat);
  const setSelectedEventId = useMapStore(s => s.setSelectedEventId);
  
  const { data: event, isLoading, isError } = useEventDetails(selectedEventId);
  const [pos, setPos] = useState({ x: -9999, y: -9999 });
  const [scrambledSummary, setScrambledSummary] = useState('');
  
  // Track position flawlessly using requestAnimationFrame and Mapbox projection
  useEffect(() => {
    if (!map || !selectedEventLngLat) return;
    
    let animationFrameId: number;
    
    const updatePosition = () => {
      const p = map.project(selectedEventLngLat as [number, number]);
      setPos({ x: p.x, y: p.y });
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
      <div className="pointer-events-auto bg-hud-bg/95 backdrop-blur-md border border-hud-border shadow-[0_0_20px_rgba(59,130,246,0.2)] flex flex-col w-96 max-h-[70vh] font-mono">
        
        {/* Header */}
        <div className="flex justify-between items-center p-3 border-b border-hud-border bg-black/40">
          <span className="text-neon-blue font-bold tracking-[0.2em] text-xs">DATA</span>
          <button 
            onClick={() => setSelectedEventId(null)}
            className="text-red-500 hover:text-red-400 cursor-crosshair text-sm font-bold tracking-widest"
          >
            [X]
          </button>
        </div>

        {/* Content Area */}
        <div className="p-5 overflow-y-auto custom-scrollbar">
          {isLoading && <p className="text-gray-500 animate-pulse text-xs tracking-widest">DECRYPTING PAYLOAD...</p>}
          {isError && <p className="text-red-500 font-bold tracking-widest">failed to load content. retry.</p>}
          
          {event && (
            <div className="flex flex-col gap-5">
              
              {/* Badges */}
              <div className="flex gap-2">
                <span 
                  className="px-2 py-1 text-[10px] font-bold tracking-[0.1em] border uppercase"
                  style={{ color: event.category_color, borderColor: event.category_color }}
                >
                  {event.category}
                </span>
                <span className="px-2 py-1 text-[10px] font-bold tracking-[0.1em] bg-red-900/40 text-red-400 border border-red-500 uppercase">
                  {event.status}
                </span>
              </div>
              
              {/* Headline */}
              <h1 className="text-sm font-bold text-white uppercase tracking-wider">{event.ai_headline}</h1>
              
              {/* AI Summary */}
              <div className="bg-black/50 p-4 border-l-2 border-neon-blue flex flex-col gap-3">
                <p className="text-gray-300 text-xs leading-relaxed whitespace-pre-wrap">
                  {scrambledSummary}
                </p>
              </div>

              {/* Verified Sources */}
              <div>
                <h3 className="text-neon-blue text-[10px] mb-3 tracking-[0.15em] uppercase">Verified Sources</h3>
                <ul className="flex flex-col gap-2">
                  {event.articles.map((article) => {
                    let domain = '';
                    try { 
                      domain = new URL(article.url).hostname.replace('www.', ''); 
                    } catch(e) {
                      domain = 'source';
                    }
                    
                    // Format link as domain/title per user request
                    const formattedTitle = article.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
                    
                    return (
                      <li key={article.id}>
                        <a 
                          href={article.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-gray-400 hover:text-neon-blue text-[10px] hover:underline cursor-crosshair block truncate tracking-wider"
                        >
                          <span className="text-neon-blue">{domain}</span>/{formattedTitle}
                        </a>
                      </li>
                    )
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
