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
  return parts.join(' // ');
}

export function MessageBubble({
  message,
  onRetry,
  onCitationActivate,
}: MessageBubbleProps): React.JSX.Element {
  const isUser = message.role === 'user';
  const isStreaming = message.status === 'streaming';
  const hasMissingCitations =
    message.done?.provenance.grounding.includes('missing_citations') ?? false;

  return (
    <article
      className={`flex flex-col gap-2 ${
        isUser ? 'items-end' : 'items-stretch'
      }`}
      data-role={message.role}
      data-status={message.status}
      data-streaming={isStreaming ? 'true' : 'false'}
    >
      <div className="text-[9px] tracking-[0.2em] text-slate-muted uppercase">
        {isUser ? 'YOU' : 'HERMES'}
      </div>

      {isUser ? (
        <p className="max-w-[85%] border border-border-subtle bg-black/50 px-3 py-2 text-xs leading-relaxed text-ivory whitespace-pre-wrap">
          {message.content}
        </p>
      ) : (
        <div className="border-l-2 border-neon-blue bg-black/40 px-3 py-2 text-xs leading-relaxed text-gray-300 whitespace-pre-wrap">
          {message.content.length > 0 ? (
            <MessageText
              content={message.content}
              sources={message.sources}
              onCitationActivate={onCitationActivate}
            />
          ) : null}
          {isStreaming ? (
            <span
              className="ml-0.5 inline-block h-3 w-1.5 animate-pulse bg-neon-blue align-middle"
              aria-label="Assistant is responding"
              data-testid="streaming-cursor"
            />
          ) : null}
        </div>
      )}

      {message.status === 'error' && message.error !== null ? (
        <div className="flex flex-col gap-2 border border-[#ef4444]/60 bg-[#ef4444]/10 px-3 py-2">
          <p className="text-[10px] tracking-wider text-[#f87171] uppercase">
            {message.error.code}
          </p>
          <p className="text-[11px] text-gray-300">{message.error.message}</p>
          <button
            type="button"
            onClick={onRetry}
            className="w-full cursor-pointer border border-[#ef4444]/60 px-2 py-1 text-[10px] font-bold tracking-widest text-[#f87171] uppercase transition-colors hover:bg-[#ef4444]/20"
          >
            RETRY
          </button>
        </div>
      ) : null}

      {message.status === 'cancelled' ? (
        <div className="flex items-center justify-between gap-2 border border-border-subtle bg-black/30 px-3 py-2">
          <span className="text-[10px] tracking-widest text-slate-muted uppercase">
            CANCELLED
          </span>
          <button
            type="button"
            onClick={onRetry}
            className="cursor-pointer border border-border-subtle px-2 py-1 text-[10px] font-bold tracking-widest text-slate-muted uppercase transition-colors hover:text-neon-blue"
          >
            RETRY
          </button>
        </div>
      ) : null}

      {message.sources.length > 0 ? (
        <div className="flex flex-col gap-1 border border-border-subtle bg-black/30 px-3 py-2">
          <span className="text-[9px] tracking-[0.2em] text-neon-blue uppercase">
            SOURCES
          </span>
          {message.sources.map((source) => {
            const timestamp = sourceTimestamp(source);
            return (
              <button
                key={`${source.kind}-${source.id}`}
                type="button"
                onClick={() => onCitationActivate?.(source)}
                className="flex cursor-pointer flex-col items-start gap-0.5 text-left transition-colors hover:text-neon-blue"
              >
                <span className="w-full truncate text-[10px] text-gray-300">
                  {source.title}
                </span>
                <span className="text-[9px] tracking-wider text-slate-muted uppercase">
                  {sourceLabel(source)}
                  {timestamp !== null ? ` // ${timestamp}` : ''}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}

      {message.done !== null ? (
        <div
          data-testid="provenance-footer"
          className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] tracking-wider text-slate-muted uppercase"
        >
          <span>
            PLOTTED{' '}
            {message.done.provenance.events +
              message.done.provenance.articles +
              message.done.provenance.timeline_nodes}
          </span>
          <span>WEB {message.done.provenance.web}</span>
          <span>BG {message.done.provenance.background ? 'YES' : 'NO'}</span>
          {hasMissingCitations ? (
            <span className="text-warning-yellow">UNGROUNDED ANSWER</span>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
