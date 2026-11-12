import { useState } from 'react';

export interface ChatComposerProps {
  isStreaming: boolean;
  onSend: (message: string) => void;
  onCancel: () => void;
}

const MAX_MESSAGE_CHARS = 4000;

export function ChatComposer({
  isStreaming,
  onSend,
  onCancel,
}: ChatComposerProps): React.JSX.Element {
  const [value, setValue] = useState('');

  const canSend = !isStreaming && value.trim().length > 0;

  const submit = (): void => {
    if (!canSend) {
      return;
    }
    onSend(value);
    setValue('');
  };

  return (
    <form
      className="flex flex-col gap-2 border-t border-hud-border bg-black/40 p-3"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        maxLength={MAX_MESSAGE_CHARS}
        rows={2}
        disabled={isStreaming}
        placeholder="ASK ABOUT THE MAP..."
        aria-label="Chat message"
        className="w-full resize-none border border-border-subtle bg-black/50 px-2 py-2 text-xs leading-relaxed text-ivory placeholder:text-slate-muted focus:border-neon-blue focus:outline-none disabled:opacity-50"
      />
      <div className="flex items-center justify-between gap-2">
        <span className="text-[9px] tracking-wider text-slate-muted uppercase">
          {value.length}/{MAX_MESSAGE_CHARS}
        </span>
        {isStreaming ? (
          <button
            type="button"
            onClick={onCancel}
            className="cursor-pointer border border-[#ef4444]/60 px-3 py-1 text-[10px] font-bold tracking-widest text-[#f87171] uppercase transition-colors hover:bg-[#ef4444]/20"
          >
            STOP
          </button>
        ) : (
          <button
            type="submit"
            disabled={!canSend}
            className="cursor-pointer border border-neon-blue bg-neon-blue/10 px-3 py-1 text-[10px] font-bold tracking-widest text-neon-blue uppercase transition-colors hover:bg-neon-blue/20 disabled:cursor-default disabled:border-border-subtle disabled:bg-transparent disabled:text-slate-muted"
          >
            TRANSMIT
          </button>
        )}
      </div>
    </form>
  );
}
