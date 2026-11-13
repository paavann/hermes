import type { ChatScopeMode } from '../store/chat-store';

export interface ScopeSelectorProps {
  mode: ChatScopeMode;
  onChange: (mode: ChatScopeMode) => void;
  disabled?: boolean;
}

const MODES: ChatScopeMode[] = ['auto', 'event', 'viewport', 'global'];

export function ScopeSelector({
  mode,
  onChange,
  disabled = false,
}: ScopeSelectorProps): React.JSX.Element {
  return (
    <div className="shrink-0 border-b border-border-subtle bg-neutral-900 px-3 py-2.5">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[9px] uppercase tracking-[0.2em] text-slate-muted/45">
          SCOPE
        </span>
        <span className="text-[8px] uppercase tracking-[0.14em] text-slate-muted/25">
          REQUEST WINDOW
        </span>
      </div>
      <div
        role="group"
        aria-label="Chat scope"
        className="grid grid-cols-4 gap-1"
      >
        {MODES.map((value) => {
          const isActive = value === mode;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={isActive}
              disabled={disabled}
              onClick={() => onChange(value)}
              className={`h-7 cursor-pointer border px-1 text-[9px] font-bold uppercase tracking-[0.12em] transition-colors focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:cursor-default disabled:opacity-50 ${
                isActive
                  ? 'border-signal-teal bg-signal-teal text-black hover:border-signal-teal-bright hover:bg-signal-teal-bright'
                  : 'border-border-subtle bg-onyx text-slate-muted/60 hover:border-signal-teal hover:text-signal-teal-bright'
              }`}
            >
              {value}
            </button>
          );
        })}
      </div>
    </div>
  );
}
