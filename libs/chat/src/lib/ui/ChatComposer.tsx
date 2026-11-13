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

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      const nextHeight = Math.min(Math.max(el.scrollHeight, 40), 120);
      el.style.height = `${nextHeight}px`;
    }
  }, [value]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent): void => {
      if (event.key !== '/' || event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }
      const target = event.target as HTMLElement | null;
      if (
        target !== null &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return;
      }
      event.preventDefault();
      textareaRef.current?.focus();
    };

    window.addEventListener('keydown', handleShortcut);
    return () => window.removeEventListener('keydown', handleShortcut);
  }, []);

  const submit = (): void => {
    if (!canSend) {
      return;
    }
    onSend(value);
    setValue('');
  };

  return (
    <form
      className="flex shrink-0 flex-col gap-2 border-t border-border-subtle bg-neutral-950 p-3 font-mono"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() =>
            onSend(
              'Provide a concise situation briefing summarizing all recent events and developments in the current map scope.',
            )
          }
          disabled={isStreaming}
          className="flex cursor-pointer items-center gap-1.5 border border-border-subtle bg-onyx px-2 py-1 text-[8px] font-bold uppercase tracking-[0.14em] text-slate-muted/65 transition-colors hover:border-neon-blue hover:text-neon-blue focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:cursor-default disabled:opacity-40"
        >
          <Lightning size={9} weight="bold" aria-hidden="true" />
          <span>SUMMARIZE EVENTS</span>
        </button>

        <span className="hidden text-[8px] uppercase tracking-[0.1em] text-slate-muted/30 select-none sm:inline">
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
        className="custom-scrollbar w-full resize-none border border-border-subtle bg-black px-2.5 py-2 text-[11px] leading-relaxed text-ivory placeholder:text-slate-muted/35 transition-colors hover:border-border-bright focus:border-neon-blue focus:outline-none focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:opacity-50"
      />

      <div className="flex items-center justify-between gap-2">
        <span className="text-[8px] uppercase tracking-[0.12em] text-slate-muted/35 tabular-nums">
          {value.length}/{MAX_MESSAGE_CHARS}
        </span>
        {isStreaming ? (
          <button
            type="button"
            onClick={onCancel}
            className="cursor-pointer border border-danger bg-danger px-3 py-1.5 text-[9px] font-bold uppercase tracking-[0.16em] text-black transition-colors hover:border-danger-bright hover:bg-danger-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            STOP
          </button>
        ) : (
          <button
            type="submit"
            disabled={!canSend}
            className="cursor-pointer border border-neon-blue px-3 py-1.5 text-[9px] font-bold uppercase tracking-[0.16em] text-neon-blue transition-colors hover:bg-neon-blue hover:text-black focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:cursor-default disabled:border-border-subtle disabled:text-slate-muted/30 disabled:hover:bg-transparent disabled:hover:text-slate-muted/30"
          >
            SEND
          </button>
        )}
      </div>
    </form>
  );
}
