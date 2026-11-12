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
      <button
        type="button"
        onClick={chat.open}
        aria-label="Open chat"
        className="absolute top-24 left-0 z-30 cursor-pointer border border-l-0 border-hud-border bg-hud-bg/95 px-2 py-3 font-mono text-[10px] font-bold tracking-[0.2em] text-neon-blue uppercase backdrop-blur-md transition-colors hover:bg-hud-border/40"
      >
        <span className="[writing-mode:vertical-rl]">CHAT</span>
      </button>
    );
  }

  return (
    <aside
      aria-label="Hermes chat"
      className="absolute top-0 left-0 z-30 flex h-full w-full flex-col border-r border-hud-border bg-hud-bg/95 font-mono backdrop-blur-md sm:w-96"
    >
      <header className="flex items-center justify-between gap-2 border-b border-hud-border bg-black/40 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold tracking-[0.2em] text-neon-blue uppercase">
            HERMES // CHAT
          </span>
          {chat.isStreaming ? (
            <span className="text-[9px] tracking-wider text-warning-yellow uppercase">
              LINK ACTIVE
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={chat.clear}
            aria-label="Clear conversation"
            className="cursor-pointer border border-border-subtle px-2 py-0.5 text-[9px] font-bold tracking-wider text-slate-muted uppercase transition-colors hover:text-neon-blue"
          >
            CLEAR
          </button>
          <button
            type="button"
            onClick={chat.close}
            aria-label="Close chat"
            className="cursor-pointer border border-[#ef4444]/60 bg-[#ef4444] px-2 py-0.5 text-[9px] font-bold tracking-wider text-black uppercase transition-colors hover:bg-[#f87171]"
          >
            CLOSE
          </button>
        </div>
      </header>

      <ScopeSelector
        mode={chat.scopeMode}
        resolved={chat.scope}
        onChange={chat.setScopeOverride}
      />

      <MessageList
        messages={chat.messages}
        isStreaming={chat.isStreaming}
        onRetry={chat.retry}
        onCitationActivate={chat.activateCitation}
      />

      <ChatComposer
        isStreaming={chat.isStreaming}
        onSend={chat.send}
        onCancel={chat.cancel}
      />
    </aside>
  );
}
