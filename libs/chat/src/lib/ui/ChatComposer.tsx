import { Lightning } from '@phosphor-icons/react';
import { useEffect, useRef, useState } from 'react';

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = !isStreaming && value.trim().length > 0;

  // Auto-resize textarea between 40px (1 line) and 120px (up to 5 lines)
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      const nextHeight = Math.min(Math.max(el.scrollHeight, 40), 120);
      el.style.height = `${nextHeight}px`;
    }
  }, [value]);

  const submit = (): void => {
    if (!canSend) {
      return;
    }
    onSend(value);
    setValue('');
  };

  return (
    <form
      className="flex flex-col gap-2 border-t border-hud-border bg-neutral-950 p-3 font-mono"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() =>
            onSend(
              'Provide a concise situation briefing summarizing all recent events and developments in the current map scope.',
            )
          }
          disabled={isStreaming}
          className="flex cursor-pointer items-center gap-1 border border-border-subtle bg-black px-2 py-0.5 text-[10px] font-bold tracking-wider text-slate-muted uppercase transition-colors hover:border-neon-blue hover:text-neon-blue focus-visible:outline-1 focus-visible:outline-neon-blue disabled:cursor-default disabled:opacity-40"
        >
          <Lightning size={10} weight="bold" />
          <span>SUMMARIZE EVENTS</span>
        </button>

        <span className="hidden text-[9px] tracking-wider text-slate-muted sm:inline select-none">
          ENTER: SEND · SHIFT+ENTER: NEWLINE
        </span>
      </div>

      <textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        maxLength={MAX_MESSAGE_CHARS}
        rows={1}
        disabled={isStreaming}
        placeholder="ASK ABOUT THE MAP..."
        aria-label="Chat message"
        className="custom-scrollbar w-full resize-none border border-border-subtle bg-black px-2.5 py-2 text-xs leading-relaxed text-ivory placeholder:text-slate-muted focus:border-neon-blue focus:outline-none focus-visible:outline-1 focus-visible:outline-neon-blue disabled:opacity-50"
      />

      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] tracking-wider text-slate-muted uppercase tabular-nums">
          {value.length}/{MAX_MESSAGE_CHARS}
        </span>
        {isStreaming ? (
          <button
            type="button"
            onClick={onCancel}
            className="cursor-pointer border border-danger bg-danger px-3 py-1 text-[10px] font-bold tracking-wider text-black uppercase transition-colors hover:border-danger-bright hover:bg-danger-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            STOP
          </button>
        ) : (
          <button
            type="submit"
            disabled={!canSend}
            className="cursor-pointer border border-neon-blue px-3 py-1 text-[10px] font-bold tracking-wider text-neon-blue uppercase transition-colors hover:bg-neon-blue hover:text-black focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:cursor-default disabled:border-border-subtle disabled:text-slate-muted disabled:hover:bg-transparent disabled:hover:text-slate-muted"
          >
            SEND
          </button>
        )}
      </div>
    </form>
  );
}
