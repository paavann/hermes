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
    <div className="flex flex-col gap-1.5 border-b border-hud-border bg-neutral-900 px-3 py-2">
      <span className="text-xs tracking-wider text-slate-muted uppercase">
        SCOPE
      </span>
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
              className={`cursor-pointer border px-1 py-1 text-[10px] font-bold tracking-wider uppercase transition-colors focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:cursor-default disabled:opacity-50 ${
                isActive
                  ? 'border-signal-teal bg-signal-teal text-black hover:border-signal-teal-bright hover:bg-signal-teal-bright'
                  : 'border-border-subtle text-slate-muted hover:border-signal-teal hover:text-signal-teal-bright'
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
