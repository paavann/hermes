import { useCallback, useEffect, useRef } from 'react';

import type {
  ChatBoundingBox,
  ChatRequest,
  ChatScope,
  ChatSource,
} from '@hermes/util-types';

import { useChatConfig } from '../config-context';
import {
  buildHistory,
  useChatStore,
} from '../store/chat-store';
import type { ChatMessage, ChatScopeMode } from '../store/chat-store';
import {
  ChatTransportError,
  chatErrorFromTransport,
  streamChat,
} from '../transport/sse';
import type { StreamChatOptions } from '../transport/sse';

export interface AutoScope {
  eventId: string | null;
  viewport: ChatBoundingBox | null;
}

export type ChatStreamFn = (options: StreamChatOptions) => Promise<void>;

export interface UseChatOptions {
  autoScope: AutoScope;
  transport?: ChatStreamFn;
  onSources?: (sources: ChatSource[]) => void;
  onCitationActivate?: (source: ChatSource) => void;
}

export interface UseChatResult {
  messages: ChatMessage[];
  isOpen: boolean;
  isStreaming: boolean;
  scope: ChatScope;
  scopeMode: ChatScopeMode;
  open: () => void;
  close: () => void;
  toggle: () => void;
  send: (message: string) => void;
  retry: () => void;
  cancel: () => void;
  clear: () => void;
  setScopeOverride: (mode: ChatScopeMode) => void;
  activateCitation: (source: ChatSource) => void;
}

/** Resolve the request scope from the session mode and current map defaults. */
export function resolveScope(
  mode: ChatScopeMode,
  auto: AutoScope,
): ChatScope {
  const eventId = auto.eventId;
  const bbox = auto.viewport;

  if (mode === 'global') {
    return { type: 'global' };
  }
  if (mode === 'event') {
    if (eventId !== null) {
      return { type: 'event', event_id: eventId };
    }
    return bbox !== null
      ? { type: 'viewport', bbox }
      : { type: 'global' };
  }
  if (mode === 'viewport') {
    return bbox !== null ? { type: 'viewport', bbox } : { type: 'global' };
  }

  if (eventId !== null) {
    return { type: 'event', event_id: eventId };
  }
  return bbox !== null ? { type: 'viewport', bbox } : { type: 'global' };
}

function lastUserIndex(messages: ChatMessage[]): number {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === 'user') {
      return index;
    }
  }
  return -1;
}

export function useChat({
  autoScope,
  transport,
  onSources,
  onCitationActivate,
}: UseChatOptions): UseChatResult {
  const config = useChatConfig();
  const abortRef = useRef<AbortController | null>(null);

  const messages = useChatStore((state) => state.messages);
  const isOpen = useChatStore((state) => state.isOpen);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const scopeMode = useChatStore((state) => state.scopeOverride);
  const scope = resolveScope(scopeMode, autoScope);

  const run = useCallback(
    async (payload: ChatRequest) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const stream = transport ?? streamChat;

      try {
        await stream({
          url: `${config.baseUrl}/api/${config.apiVer}/chat`,
          payload,
          signal: controller.signal,
          onEvent: (event) => {
            useChatStore.getState().applyEvent(event);
            if (event.type === 'sources') {
              onSources?.(event.sources);
            }
          },
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        const failure: ChatTransportError | null =
          error instanceof ChatTransportError ? error : null;
        useChatStore.getState().fail(
          failure
            ? chatErrorFromTransport(failure)
            : {
                code: 'INTERNAL_ERROR',
                message:
                  error instanceof Error
                    ? error.message
                    : 'The chat request failed.',
                retryable: true,
              },
        );
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
      }
    },
    [config.apiVer, config.baseUrl, onSources, transport],
  );

  const send = useCallback(
    (content: string) => {
      const store = useChatStore.getState();
      if (store.isStreaming || !content.trim()) {
        return;
      }

      const history = buildHistory(store.messages);
      const payload: ChatRequest = {
        message: content.trim(),
        history,
        scope: resolveScope(store.scopeOverride, autoScope),
      };
      if (!store.send(content)) {
        return;
      }
      void run(payload);
    },
    [autoScope, run],
  );

  const retry = useCallback(() => {
    const store = useChatStore.getState();
    if (store.isStreaming) {
      return;
    }

    const index = lastUserIndex(store.messages);
    if (index < 0) {
      return;
    }
    const userMessage = store.messages[index];
    const payload: ChatRequest = {
      message: userMessage.content,
      history: buildHistory(store.messages.slice(0, index)),
      scope: resolveScope(store.scopeOverride, autoScope),
    };
    if (!store.retry()) {
      return;
    }
    void run(payload);
  }, [autoScope, run]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    useChatStore.getState().cancel();
    onSources?.([]);
  }, [onSources]);

  const close = useCallback(() => {
    if (useChatStore.getState().isStreaming) {
      abortRef.current?.abort();
      abortRef.current = null;
      useChatStore.getState().cancel();
    }
    useChatStore.getState().setOpen(false);
    onSources?.([]);
  }, [onSources]);

  const open = useCallback(() => {
    useChatStore.getState().setOpen(true);
  }, []);

  const toggle = useCallback(() => {
    if (useChatStore.getState().isOpen) {
      close();
    } else {
      open();
    }
  }, [close, open]);

  const clear = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    useChatStore.getState().cancel();
    useChatStore.getState().clear();
    onSources?.([]);
  }, [onSources]);

  const setScopeOverride = useCallback((mode: ChatScopeMode) => {
    useChatStore.getState().setScopeOverride(mode);
  }, []);

  const activateCitation = useCallback(
    (source: ChatSource) => {
      if (source.kind === 'web') {
        if (source.url) {
          window.open(source.url, '_blank', 'noopener,noreferrer');
        }
        return;
      }
      if (
        source.event_id !== null &&
        source.latitude !== null &&
        source.longitude !== null
      ) {
        onCitationActivate?.(source);
      }
    },
    [onCitationActivate],
  );

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return {
    messages,
    isOpen,
    isStreaming,
    scope,
    scopeMode,
    open,
    close,
    toggle,
    send,
    retry,
    cancel,
    clear,
    setScopeOverride,
    activateCitation,
  };
}
