import { SidebarSimple, Trash, X } from '@phosphor-icons/react';
import { useEffect } from 'react';

import type { ChatSource } from '@hermes/util-types';

import { useChat } from '../hooks/use-chat';
import type { AutoScope, ChatStreamFn } from '../hooks/use-chat';
import { ChatComposer } from './ChatComposer';
import { MessageList } from './MessageList';
import { ScopeSelector } from './ScopeSelector';

export interface ChatPanelProps {
  autoScope: AutoScope;
  transport?: ChatStreamFn;
  onSources?: (sources: ChatSource[]) => void;
  onCitationActivate?: (source: ChatSource) => void;
}

export function ChatPanel({
  autoScope,
  transport,
  onSources,
  onCitationActivate,
}: ChatPanelProps): React.JSX.Element {
  const chat = useChat({
    autoScope,
    transport,
    onSources,
    onCitationActivate,
  });
  const { isOpen, close } = chat;

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        close();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, close]);

  if (!chat.isOpen) {
    return (
      <div
        data-testid="chat-rail"
        className="absolute bottom-7 left-0 top-12 z-20 flex w-12 flex-col items-center border-r border-border-subtle bg-neutral-900 pt-3 font-mono select-none"
      >
        <button
          type="button"
          onClick={chat.open}
          aria-label="Open chat"
          className="flex h-10 w-10 cursor-pointer items-center justify-center text-bone/70 transition-colors hover:text-white focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:-outline-offset-2"
        >
          <SidebarSimple size={18} weight="bold" aria-hidden="true" />
        </button>

        <div className="mt-6 flex flex-col items-center gap-3">
          <span className="h-6 w-px bg-border-subtle" aria-hidden="true" />
          <span className="text-[9px] font-bold uppercase tracking-[0.28em] text-slate-muted/50 [writing-mode:vertical-lr]">
            EXPLORE
          </span>
        </div>

        <span className="mt-auto mb-3 h-1.5 w-1.5 bg-neon-blue/60" aria-hidden="true" />
      </div>
    );
  }

  return (
    <aside
      aria-label="Hermes chat"
      className="absolute bottom-7 left-0 top-12 z-30 flex w-full flex-col border-r border-border-subtle bg-neutral-900 font-mono sm:w-[24rem]"
    >
      <header className="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-border-subtle bg-black px-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-ivory">
            EXPLORE
          </span>
          {chat.messages.length > 0 ? (
            <span className="border border-border-subtle bg-onyx px-1.5 py-0.5 text-[9px] font-bold tabular-nums text-slate-muted">
              {String(chat.messages.length).padStart(2, '0')}
            </span>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            onClick={chat.clear}
            aria-label="Clear conversation"
            title="Clear conversation"
            className="flex h-7 w-7 cursor-pointer items-center justify-center border border-signal-teal bg-signal-teal text-black uppercase transition-colors hover:border-signal-teal-bright hover:bg-signal-teal-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            <Trash size={12} weight="bold" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={chat.close}
            aria-label="Close chat"
            title="Close chat"
            className="flex h-7 w-7 cursor-pointer items-center justify-center border border-danger bg-danger text-black uppercase transition-colors hover:border-danger-bright hover:bg-danger-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            <X size={12} weight="bold" aria-hidden="true" />
          </button>
        </div>
      </header>

      <ScopeSelector mode={chat.scopeMode} onChange={chat.setScopeOverride} />

      <MessageList
        messages={chat.messages}
        isStreaming={chat.isStreaming}
        onRetry={chat.retry}
        onCitationActivate={chat.activateCitation}
        onSendPrompt={chat.send}
        scopeMode={chat.scopeMode}
      />

      <ChatComposer
        isStreaming={chat.isStreaming}
        onSend={chat.send}
        onCancel={chat.cancel}
      />
    </aside>
  );
}
