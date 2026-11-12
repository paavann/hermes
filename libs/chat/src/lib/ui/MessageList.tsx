import { useEffect, useRef } from 'react';

import type { ChatSource } from '@hermes/util-types';

import type { ChatMessage } from '../store/chat-store';
import { MessageBubble } from './MessageBubble';

export interface MessageListProps {
  messages: readonly ChatMessage[];
  isStreaming: boolean;
  onRetry: () => void;
  onCitationActivate?: (source: ChatSource) => void;
}

export function MessageList({
  messages,
  isStreaming,
  onRetry,
  onCitationActivate,
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
      <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-[10px] tracking-[0.2em] text-slate-muted uppercase">
          NO TRANSMISSIONS
        </p>
        <p className="text-[11px] leading-relaxed text-gray-500">
          Ask about the events in the current map scope. Answers cite the
          plottings behind each claim.
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
