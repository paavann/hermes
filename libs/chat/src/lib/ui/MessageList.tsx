import { Lightning } from '@phosphor-icons/react';
import { useEffect, useRef } from 'react';

import type { ChatSource } from '@hermes/util-types';

import type { ChatMessage, ChatScopeMode } from '../store/chat-store';
import { MessageBubble } from './MessageBubble';

export interface MessageListProps {
  messages: readonly ChatMessage[];
  isStreaming: boolean;
  onRetry: () => void;
  onCitationActivate?: (source: ChatSource) => void;
  onSendPrompt?: (prompt: string) => void;
  scopeMode?: ChatScopeMode;
}

export function MessageList({
  messages,
  isStreaming,
  onRetry,
  onCitationActivate,
  onSendPrompt,
  scopeMode = 'auto',
}: MessageListProps): React.JSX.Element {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = endRef.current;
    if (node && typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ block: 'end' });
    }
  }, [messages, isStreaming]);

  if (messages.length === 0) {
    return (
      <div className="custom-scrollbar flex flex-1 flex-col gap-5 overflow-y-auto p-4 font-mono">
        {/* Briefing Hero Card */}
        <div className="flex flex-col gap-3 border border-border-subtle bg-neutral-950 p-3.5">
          <div className="flex items-center justify-between border-b border-border-subtle pb-2 text-[10px] tracking-wider uppercase">
            <span className="font-bold text-neon-blue">BRIEFING</span>
            <span className="text-slate-muted">SCOPE · {scopeMode.toUpperCase()}</span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-xs font-bold tracking-wider text-ivory uppercase">
              INTELLIGENCE BRIEFING
            </span>
            <p className="text-[11px] leading-relaxed text-gray-400">
              Synthesize events, casualties, and critical developments within the current map scope.
            </p>
          </div>

          <button
            type="button"
            onClick={() =>
              onSendPrompt?.(
                'Provide a concise situation briefing summarizing all recent events and developments in the current map scope.',
              )
            }
            disabled={isStreaming}
            className="flex cursor-pointer items-center justify-center gap-2 border border-neon-blue bg-neon-blue/10 px-3 py-2 text-xs font-bold tracking-wider text-neon-blue uppercase transition-colors hover:bg-neon-blue hover:text-black focus-visible:outline-1 focus-visible:outline-neon-blue disabled:cursor-default disabled:opacity-50"
          >
            <Lightning size={14} weight="bold" />
            <span>SUMMARIZE EVENTS</span>
          </button>
        </div>

        {/* Quick queries */}
        <div className="flex flex-col gap-2">
          <span className="text-[10px] font-bold tracking-wider text-slate-muted uppercase">
            QUICK QUERIES
          </span>
          <div className="flex flex-col gap-1.5">
            {[
              {
                label: 'CRITICAL INCIDENTS',
                prompt: 'Identify and detail high-severity incidents in the current scope.',
              },
              {
                label: 'TIMELINE PROGRESSION',
                prompt: 'Analyze the chronological progression of key events in this region.',
              },
              {
                label: 'SOURCE EVIDENCE',
                prompt: 'What are the primary confirmed news sources and evidence for these events?',
              },
            ].map((item) => (
              <button
                key={item.label}
                type="button"
                onClick={() => onSendPrompt?.(item.prompt)}
                disabled={isStreaming}
                className="flex cursor-pointer items-center justify-between border border-border-subtle bg-black px-3 py-2 text-left text-[11px] text-gray-300 transition-colors hover:border-signal-teal hover:text-white focus-visible:outline-1 focus-visible:outline-neon-blue disabled:cursor-default disabled:opacity-50"
              >
                <span>{item.label}</span>
                <span className="text-[10px] text-slate-muted">↵</span>
              </button>
            ))}
          </div>
        </div>

        {/* Minimal grounding guarantee */}
        <p className="mt-auto text-[10px] leading-relaxed text-slate-muted">
          Ask about the events in the current map scope. Each answer cites the evidence behind its claims.
        </p>
      </div>
    );
  }

  return (
    <div className="custom-scrollbar flex flex-1 flex-col gap-4 overflow-y-auto px-3 py-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onRetry={onRetry}
          onCitationActivate={onCitationActivate}
        />
      ))}
      <div ref={endRef} />
    </div>
  );
}
