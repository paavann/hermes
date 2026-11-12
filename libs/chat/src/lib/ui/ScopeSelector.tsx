import type { ChatScope } from '@hermes/util-types';

import type { ChatScopeMode } from '../store/chat-store';

export interface ScopeSelectorProps {
  mode: ChatScopeMode;
  resolved: ChatScope;
  onChange: (mode: ChatScopeMode) => void;
  disabled?: boolean;
}

const MODES: ChatScopeMode[] = ['auto', 'event', 'viewport', 'global'];

function scopeSummary(scope: ChatScope): string {
  switch (scope.type) {
    case 'event':
      return 'EVENT LOCK';
    case 'viewport':
      return 'VIEWPORT';
    case 'global':
      return 'GLOBAL';
  }
}

export function ScopeSelector({
  mode,
  resolved,
  onChange,
  disabled = false,
}: ScopeSelectorProps): React.JSX.Element {
  return (
    <div className="flex flex-col gap-1 border-b border-hud-border bg-black/30 px-3 py-2">
      <div className="flex items-center justify-between">
        <span className="text-[9px] tracking-[0.2em] text-slate-muted uppercase">
          SCOPE
        </span>
        <span className="text-[9px] tracking-wider text-neon-blue uppercase">
          {scopeSummary(resolved)}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-1">
        {MODES.map((value) => {
          const isActive = value === mode;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={isActive}
              disabled={disabled}
              onClick={() => onChange(value)}
              className={`cursor-pointer border px-1 py-1 text-[9px] font-bold tracking-widest uppercase transition-colors disabled:cursor-default disabled:opacity-50 ${
                isActive
                  ? 'border-neon-blue bg-neon-blue/10 text-neon-blue'
                  : 'border-border-subtle text-slate-muted hover:border-hud-border hover:text-gray-300'
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
