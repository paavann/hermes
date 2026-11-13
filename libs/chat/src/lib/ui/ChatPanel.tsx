import { SidebarSimple } from '@phosphor-icons/react';
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
        className="absolute top-0 left-0 z-20 flex h-full w-12 flex-col items-center border-r border-hud-border bg-neutral-900 pt-4 font-mono select-none"
      >
        <button
          type="button"
          onClick={chat.open}
          aria-label="Open chat"
          className="flex h-10 w-10 cursor-pointer items-center justify-center text-white transition-colors hover:text-white focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:-outline-offset-2"
        >
          <SidebarSimple size={18} weight="bold" aria-hidden="true" />
        </button>
        <div className="mt-8 flex flex-col items-center gap-1.5 opacity-60 pointer-events-none">
          <span className="text-[9px] font-bold tracking-[0.25em] text-slate-muted [writing-mode:vertical-lr] uppercase">
            CHAT
          </span>
        </div>
      </div>
    );
  }

  return (
    <aside
      aria-label="Hermes chat"
      className="absolute top-0 left-0 z-30 flex h-full w-full flex-col border-r border-hud-border bg-neutral-900 font-mono sm:w-96"
    >
      <header className="flex items-center justify-between gap-2 border-b border-hud-border bg-neutral-900 px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold tracking-[0.2em] text-ivory uppercase">
            EXPLORE
          </span>
          {chat.messages.length > 0 ? (
            <span className="border border-border-subtle bg-black px-1.5 py-0.5 text-[9px] font-bold text-slate-muted tabular-nums">
              {chat.messages.length}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={chat.clear}
            aria-label="Clear conversation"
            className="cursor-pointer border border-signal-teal bg-signal-teal px-2 py-1 text-[10px] font-bold tracking-wider text-black uppercase transition-colors hover:border-signal-teal-bright hover:bg-signal-teal-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            CLEAR
          </button>
          <button
            type="button"
            onClick={chat.close}
            aria-label="Close chat"
            className="cursor-pointer border border-danger bg-danger px-2 py-1 text-[10px] font-bold tracking-wider text-black uppercase transition-colors hover:border-danger-bright hover:bg-danger-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            CLOSE
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
