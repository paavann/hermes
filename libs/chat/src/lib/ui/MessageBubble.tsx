import { CaretDown, CaretRight } from '@phosphor-icons/react';
import { useState } from 'react';

import type { ChatSource } from '@hermes/util-types';

import type { ChatMessage } from '../store/chat-store';
import { MessageText } from './MessageText';

export interface MessageBubbleProps {
  message: ChatMessage;
  onRetry: () => void;
  onCitationActivate?: (source: ChatSource) => void;
}

function sourceTimestamp(source: ChatSource): string | null {
  if (source.published_at !== null) {
    return `${source.published_at.slice(0, 16).replace('T', ' ')}Z`;
  }
  if (source.retrieved_at !== null) {
    return `${source.retrieved_at.slice(0, 16).replace('T', ' ')}Z RETRIEVED`;
  }
  return null;
}

function sourceLabel(source: ChatSource): string {
  const parts = [source.kind.toUpperCase()];
  if (source.source_name !== null) {
    parts.push(source.source_name);
  }
  if (source.is_external) {
    parts.push('EXTERNAL');
  }
  return parts.join(' · ');
}

export function MessageBubble({
  message,
  onRetry,
  onCitationActivate,
}: MessageBubbleProps): React.JSX.Element {
  const [isSourcesOpen, setIsSourcesOpen] = useState(false);
  const isUser = message.role === 'user';
  const isStreaming = message.status === 'streaming';
  const hasMissingCitations =
    message.done?.provenance.grounding.includes('missing_citations') ?? false;

  return (
    <article
      className={`flex flex-col gap-1.5 ${
        isUser ? 'items-end' : 'items-stretch'
      }`}
      data-role={message.role}
      data-status={message.status}
      data-streaming={isStreaming ? 'true' : 'false'}
    >
      <div className="flex w-full items-center gap-2 text-[9px] uppercase tracking-[0.2em]">
        {isUser ? (
          <>
            <span className="h-px flex-1 bg-border-subtle/50" aria-hidden="true" />
            <span className="text-slate-muted/45">YOU</span>
          </>
        ) : (
          <>
            <span className="h-1 w-1 bg-neon-blue" aria-hidden="true" />
            <span className="font-bold text-neon-blue">HERMES</span>
            <span className="h-px flex-1 bg-border-subtle/50" aria-hidden="true" />
          </>
        )}
      </div>

      {isUser ? (
        <div className="max-w-[92%] border border-border-bright bg-graphite px-3 py-2 text-[11px] leading-relaxed whitespace-pre-wrap text-ivory">
          {message.content}
        </div>
      ) : (
        <div className="border border-border-subtle border-l-2 border-l-neon-blue bg-black px-3 py-2.5 text-[11px] leading-relaxed text-bone/85">
          {isStreaming && message.content.length === 0 ? (
            <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.16em] text-slate-muted">
              <span className="inline-block h-1.5 w-1.5 animate-pulse bg-neon-blue" aria-hidden="true" />
              <span>SYNTHESIZING RESPONSE...</span>
              <span
                className="inline-block h-3 w-1.5 animate-pulse bg-neon-blue align-middle"
                aria-label="Assistant is responding"
                data-testid="streaming-cursor"
              />
            </div>
          ) : null}

          {message.content.length > 0 ? (
            <div>
              <MessageText
                content={message.content}
                sources={message.sources}
                onCitationActivate={onCitationActivate}
              />
              {isStreaming ? (
                <span
                  className="ml-0.5 inline-block h-3 w-1.5 animate-pulse bg-neon-blue align-middle"
                  aria-label="Assistant is responding"
                  data-testid="streaming-cursor"
                />
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      {message.status === 'error' && message.error !== null ? (
        <div className="flex flex-col gap-2 border border-danger bg-black px-3 py-2.5">
          <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-danger-bright">
            {message.error.code}
          </p>
          <p className="text-[10px] leading-relaxed text-bone/70">
            {message.error.message}
          </p>
          <button
            type="button"
            onClick={onRetry}
            className="w-full cursor-pointer border border-signal-teal bg-signal-teal px-2 py-1.5 text-[9px] font-bold uppercase tracking-[0.16em] text-black transition-colors hover:border-signal-teal-bright hover:bg-signal-teal-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            RETRY
          </button>
        </div>
      ) : null}

      {message.status === 'cancelled' ? (
        <div className="flex items-center justify-between gap-2 border border-border-subtle bg-black px-3 py-2">
          <span className="text-[9px] uppercase tracking-[0.16em] text-slate-muted/55">
            CANCELLED
          </span>
          <button
            type="button"
            onClick={onRetry}
            className="cursor-pointer border border-signal-teal bg-signal-teal px-2 py-1 text-[9px] font-bold uppercase tracking-[0.16em] text-black transition-colors hover:border-signal-teal-bright hover:bg-signal-teal-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            RETRY
          </button>
        </div>
      ) : null}

      {message.sources.length > 0 ? (
        <div className="border border-border-subtle bg-black">
          <button
            type="button"
            onClick={() => setIsSourcesOpen(!isSourcesOpen)}
            className="flex w-full cursor-pointer items-center justify-between px-3 py-2 text-left transition-colors hover:bg-white/[0.02] focus-visible:outline-1 focus-visible:outline-neon-blue"
            aria-expanded={isSourcesOpen}
          >
            <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-[0.16em] text-neon-blue">
              {isSourcesOpen ? (
                <CaretDown size={10} weight="bold" aria-hidden="true" />
              ) : (
                <CaretRight size={10} weight="bold" aria-hidden="true" />
              )}
              <span>SOURCES ({message.sources.length})</span>
            </div>
            <span className="text-[8px] uppercase tracking-[0.14em] text-slate-muted/35">
              {isSourcesOpen ? 'COLLAPSE' : 'EXPAND'}
            </span>
          </button>

          {isSourcesOpen ? (
            <div className="flex flex-col border-t border-border-subtle">
              {message.sources.map((source, idx) => {
                const timestamp = sourceTimestamp(source);
                return (
                  <button
                    key={`${source.kind}-${source.id}`}
                    type="button"
                    onClick={() => onCitationActivate?.(source)}
                    className="flex cursor-pointer items-start gap-2 border-b border-border-subtle/60 px-3 py-2 text-left transition-colors last:border-b-0 hover:bg-white/[0.02] focus-visible:outline-1 focus-visible:outline-neon-blue"
                  >
                    <span className="mt-0.5 tabular-nums text-[8px] text-slate-muted/30">
                      {String(idx + 1).padStart(2, '0')}
                    </span>
                    <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="w-full truncate text-[10px] text-bone/75">
                        {source.title}
                      </span>
                      <span className="text-[8px] uppercase tracking-[0.12em] text-slate-muted/40">
                        {sourceLabel(source)}
                        {timestamp !== null ? ` · ${timestamp}` : ''}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}

      {message.done !== null ? (
        <div
          data-testid="provenance-footer"
          className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[8px] uppercase tracking-[0.14em] text-slate-muted/40 tabular-nums"
        >
          <span>
            PLOTTED{' '}
            {message.done.provenance.events +
              message.done.provenance.articles +
              message.done.provenance.timeline_nodes}
          </span>
          <span className="text-border-bright">·</span>
          <span>WEB {message.done.provenance.web}</span>
          <span className="text-border-bright">·</span>
          <span>BG {message.done.provenance.background ? 'YES' : 'NO'}</span>
          {hasMissingCitations ? (
            <>
              <span className="text-border-bright">·</span>
              <span className="text-warning-yellow">UNGROUNDED ANSWER</span>
            </>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
