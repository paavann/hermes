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

const QUICK_QUERIES: readonly {
  readonly index: string;
  readonly label: string;
  readonly prompt: string;
}[] = [
  {
    index: '01',
    label: 'CRITICAL INCIDENTS',
    prompt: 'Identify and detail high-severity incidents in the current scope.',
  },
  {
    index: '02',
    label: 'TIMELINE PROGRESSION',
    prompt: 'Analyze the chronological progression of key events in this region.',
  },
  {
    index: '03',
    label: 'SOURCE EVIDENCE',
    prompt:
      'What are the primary confirmed news sources and evidence for these events?',
  },
] as const;

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
      <div className="custom-scrollbar flex flex-1 flex-col gap-5 overflow-y-auto p-3.5">
        <div className="border border-border-subtle bg-onyx">
          <div className="flex items-center justify-between border-b border-border-subtle bg-black px-3 py-2 text-[9px] uppercase tracking-[0.18em]">
            <span className="flex items-center gap-2 font-bold text-neon-blue">
              <span className="h-1.5 w-1.5 bg-neon-blue" aria-hidden="true" />
              <span>BRIEFING</span>
            </span>
            <span className="tabular-nums text-slate-muted/40">
              SCOPE · {scopeMode.toUpperCase()}
            </span>
          </div>

          <div className="space-y-4 p-4">
            <div>
              <p className="font-display text-lg font-medium leading-tight tracking-[-0.02em] text-ivory">
                Intelligence briefing
              </p>
              <p className="mt-2 text-[10px] leading-relaxed text-slate-muted/70">
                Synthesize events, casualties, and critical developments within
                the current map scope.
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
              className="flex w-full cursor-pointer items-center justify-between gap-2 border border-neon-blue bg-neon-blue px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.16em] text-black transition-colors hover:border-ivory hover:bg-ivory focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:cursor-default disabled:opacity-50"
            >
              <span className="flex items-center gap-2">
                <Lightning size={12} weight="bold" aria-hidden="true" />
                <span>SUMMARIZE EVENTS</span>
              </span>
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-[9px] uppercase tracking-[0.18em]">
            <span className="font-bold text-slate-muted/55">QUICK QUERIES</span>
            <span className="text-slate-muted/30">03</span>
          </div>
          <div className="border-t border-border-subtle">
            {QUICK_QUERIES.map((item) => (
              <button
                key={item.label}
                type="button"
                onClick={() => onSendPrompt?.(item.prompt)}
                disabled={isStreaming}
                className="group flex w-full cursor-pointer items-center gap-3 border-b border-border-subtle/60 px-1 py-2.5 text-left transition-colors hover:bg-white/[0.02] focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:cursor-default disabled:opacity-50"
              >
                <span className="tabular-nums text-[9px] text-slate-muted/30">
                  {item.index}
                </span>
                <span className="min-w-0 flex-1 truncate text-[10px] uppercase tracking-[0.1em] text-bone/70 transition-colors group-hover:text-ivory">
                  {item.label}
                </span>
                <span className="text-[10px] text-slate-muted/30 transition-colors group-hover:text-neon-blue">
                  ↵
                </span>
              </button>
            ))}
          </div>
        </div>

        <p className="mt-auto border-t border-border-subtle pt-3 text-[9px] leading-relaxed tracking-[0.04em] text-slate-muted/40">
          Ask about the events in the current map scope. Each answer cites the
          evidence behind its claims.
        </p>
      </div>
    );
  }

  return (
    <div className="custom-scrollbar flex flex-1 flex-col gap-5 overflow-y-auto px-3 py-4">
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
