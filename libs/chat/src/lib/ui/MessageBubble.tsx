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
      <div className="flex items-center gap-2 text-[10px] tracking-[0.2em] uppercase">
        {isUser ? (
          <span className="text-slate-muted">YOU</span>
        ) : (
          <span className="font-bold text-neon-blue">HERMES</span>
        )}
      </div>

      {isUser ? (
        <div className="max-w-[90%] border border-border-subtle bg-neutral-900 px-3 py-2 text-xs leading-relaxed text-ivory whitespace-pre-wrap">
          {message.content}
        </div>
      ) : (
        <div className="border border-border-subtle border-l-2 border-l-neon-blue bg-black px-3 py-2.5 text-xs leading-relaxed text-neutral-200">
          {isStreaming && message.content.length === 0 ? (
            <div className="flex items-center gap-2 text-[11px] text-slate-muted">
              <span className="inline-block h-1.5 w-1.5 animate-pulse bg-neon-blue" />
              <span className="tracking-wider uppercase">SYNTHESIZING RESPONSE...</span>
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
        <div className="flex flex-col gap-2 border border-danger bg-black px-3 py-2">
          <p className="text-[10px] font-bold tracking-wider text-danger-bright uppercase">
            {message.error.code}
          </p>
          <p className="text-[11px] text-gray-300">{message.error.message}</p>
          <button
            type="button"
            onClick={onRetry}
            className="w-full cursor-pointer border border-signal-teal bg-signal-teal px-2 py-1 text-[10px] font-bold tracking-wider text-black uppercase transition-colors hover:border-signal-teal-bright hover:bg-signal-teal-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            RETRY
          </button>
        </div>
      ) : null}

      {message.status === 'cancelled' ? (
        <div className="flex items-center justify-between gap-2 border border-border-subtle bg-black px-3 py-2">
          <span className="text-[10px] tracking-wider text-slate-muted uppercase">
            CANCELLED
          </span>
          <button
            type="button"
            onClick={onRetry}
            className="cursor-pointer border border-signal-teal bg-signal-teal px-2 py-1 text-[10px] font-bold tracking-wider text-black uppercase transition-colors hover:border-signal-teal-bright hover:bg-signal-teal-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            RETRY
          </button>
        </div>
      ) : null}

      {message.sources.length > 0 ? (
        <div className="flex flex-col border border-border-subtle bg-black">
          <button
            type="button"
            onClick={() => setIsSourcesOpen(!isSourcesOpen)}
            className="flex cursor-pointer items-center justify-between px-3 py-1.5 text-left transition-colors hover:bg-neutral-900 focus-visible:outline-1 focus-visible:outline-neon-blue"
            aria-expanded={isSourcesOpen}
          >
            <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-wider text-neon-blue uppercase">
              {isSourcesOpen ? (
                <CaretDown size={12} weight="bold" />
              ) : (
                <CaretRight size={12} weight="bold" />
              )}
              <span>SOURCES ({message.sources.length})</span>
            </div>
            <span className="text-[9px] tracking-wider text-slate-muted uppercase">
              {isSourcesOpen ? 'COLLAPSE' : 'EXPAND'}
            </span>
          </button>

          {isSourcesOpen ? (
            <div className="flex flex-col gap-2 border-t border-border-subtle px-3 py-2">
              {message.sources.map((source) => {
                const timestamp = sourceTimestamp(source);
                return (
                  <button
                    key={`${source.kind}-${source.id}`}
                    type="button"
                    onClick={() => onCitationActivate?.(source)}
                    className="flex cursor-pointer flex-col items-start gap-0.5 text-left transition-colors hover:text-neon-blue focus-visible:outline-1 focus-visible:outline-neon-blue"
                  >
                    <span className="w-full truncate text-[10px] text-gray-300">
                      {source.title}
                    </span>
                    <span className="text-[9px] tracking-wider text-slate-muted uppercase">
                      {sourceLabel(source)}
                      {timestamp !== null ? ` · ${timestamp}` : ''}
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
          className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[9px] tracking-wider text-slate-muted uppercase tabular-nums"
        >
          <span>
            PLOTTED{' '}
            {message.done.provenance.events +
              message.done.provenance.articles +
              message.done.provenance.timeline_nodes}
          </span>
          <span>·</span>
          <span>WEB {message.done.provenance.web}</span>
          <span>·</span>
          <span>BG {message.done.provenance.background ? 'YES' : 'NO'}</span>
          {hasMissingCitations ? (
            <>
              <span>·</span>
              <span className="text-warning-yellow">UNGROUNDED ANSWER</span>
            </>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
