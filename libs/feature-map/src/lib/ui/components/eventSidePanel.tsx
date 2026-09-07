import { useMapStore } from '../../store/store'
import { useEventDetails } from '../../hooks/eventDetails'



export function EventSidePanel() {
    const selectedEventId = useMapStore((s) => s.selectedEventId)
    const setSelectedEventId = useMapStore((s) => s.setSelectedEventId)
    const { data: event, isLoading, isError } = useEventDetails(selectedEventId)


    if(!selectedEventId) {
        return null
    } else {
        return (
            <div className="fixed top-0 right-0 w-96 h-full bg-hud-bg/95 backdrop-blur-md border-l border-hud-border z-20 flex flex-col shadow">

                {/* Header */}
                <div className="p-4 border-b border-hud-border flex justify-between items-center">
                    <h2 className="text-hud-glow font-mono font-bold">EVENT_DATA_STREAM</h2>
                    <button 
                        onClick={() => setSelectedEventId(null)}
                        className="text-gray-400 hover:text-white font-mono cursor-pointer">
                        [X] CLOSE
                    </button>
                </div>

                {/* Content Area */}
                <div className="p-6 overflow-y-auto flex-1">
                    {isLoading && <p className="text-gray-400 font-mono animate-pulse">DECRYPTING PAYLOAD...</p>}
                    {isError && <p className="text-red-500 font-mono">ERROR: SIGNAL LOST</p>}

                    {event && (
                        <div className="flex flex-col gap-6">
                            {/* Badges */}
                            <div className="flex gap-2">
                                <span 
                                    className="px-2 py-1 text-xs font-mono font-bold uppercase border"
                                    style={{ color: event.category_color, borderColor: event.category_color }}>
                                    {event.category}
                                </span>
                                <span className="px-2 py-1 text-xs font-mono bg-red-900/50 text-red-400 border border-red-500 uppercase">
                                    {event.status}
                                </span>
                            </div>

                            {/* Headline & Summary */}
                            <h1 className="text-2xl font-bold text-white">{event.ai_headline}</h1>
                            <p className="text-gray-300 leading-relaxed text-sm bg-black/30 p-4 border-l-2 border-hud-glow">
                                {event.ai_summary}
                            </p>

                            {/* Source Links */}
                            <div>
                                <h3 className="text-hud-glow font-mono text-sm mb-3">/// VERIFIED SOURCES</h3>
                                <ul className="flex flex-col gap-2">
                                    {event.articles.map((article) => (
                                    <li key={article.id}>
                                        <a 
                                            href={article.url} 
                                            target="_blank" 
                                            rel="noopener noreferrer"
                                            className="text-blue-400 hover:text-blue-300 text-sm hover:underline flex items-center gap-2"
                                        >
                                            <span className="text-xs text-gray-500">[{new Date(article.published_at || '').toLocaleDateString()}]</span>
                                            {article.title}
                                        </a>
                                    </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        )
    }
}