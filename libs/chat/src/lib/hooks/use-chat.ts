import { useCallback, useEffect, useRef } from 'react';
import type {
  ChatBoundingBox,
  ChatError,
  ChatRequest,
  ChatScope,
  ChatSource,
} from '@hermes/util-types';
import { isFocusableSource } from '../citations';
import { useChatConfig } from '../config-context';
import {
  buildHistory,
  findLastUserIndex,
  useChatStore,
} from '../store/chat-store';
import type { ChatMessage, ChatScopeMode } from '../store/chat-store';
import {
  ChatTransportErr,
  chatErrorFromTransport,
  streamChat,
} from '../transport/sse';
import type { StreamChatOptions } from '../types/sse.types';

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
  { eventId, viewport: bbox }: AutoScope,
): ChatScope {
  if ((mode === 'auto' || mode === 'event') && eventId !== null) {
    return { type: 'event', event_id: eventId };
  }
  if (mode !== 'global' && bbox !== null) {
    return { type: 'viewport', bbox };
  }
  return { type: 'global' };
}

function normalizeTransportError(error: unknown): ChatError {
  if (error instanceof ChatTransportErr) {
    return chatErrorFromTransport(error);
  }
  return {
    code: 'INTERNAL_ERROR',
    message:
      error instanceof Error ? error.message : 'The chat request failed.',
    retryable: true,
  };
}

export function useChat({
  autoScope,
  transport,
  onSources,
  onCitationActivate,
}: UseChatOptions): UseChatResult {
  const config = useChatConfig();
  const abortRef = useRef<AbortController | null>(null);
  const latestRef = useRef({ autoScope, onSources, onCitationActivate });

  useEffect(() => {
    latestRef.current = { autoScope, onSources, onCitationActivate };
  });

  const messages = useChatStore((state) => state.messages);
  const isOpen = useChatStore((state) => state.isOpen);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const scopeMode = useChatStore((state) => state.scopeOverride);
  const scope = resolveScope(scopeMode, autoScope);

  const abortStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const run = useCallback(
    async (payload: ChatRequest) => {
      abortStream();
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
              latestRef.current.onSources?.(event.sources);
            }
          },
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        useChatStore.getState().fail(normalizeTransportError(error));
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
      }
    },
    [abortStream, config.apiVer, config.baseUrl, transport],
  );

  const send = useCallback(
    (content: string) => {
      const store = useChatStore.getState();
      if (store.isStreaming || !content.trim()) {
        return;
      }
      const payload: ChatRequest = {
        message: content.trim(),
        history: buildHistory(store.messages),
        scope: resolveScope(store.scopeOverride, latestRef.current.autoScope),
      };
      if (!store.send(content)) {
        return;
      }
      void run(payload);
    },
    [run],
  );

  const retry = useCallback(() => {
    const store = useChatStore.getState();
    if (store.isStreaming) {
      return;
    }
    const index = findLastUserIndex(store.messages);
    if (index < 0) {
      return;
    }
    const payload: ChatRequest = {
      message: store.messages[index].content,
      history: buildHistory(store.messages.slice(0, index)),
      scope: resolveScope(store.scopeOverride, latestRef.current.autoScope),
    };
    if (!store.retry()) {
      return;
    }
    void run(payload);
  }, [run]);

  const cancel = useCallback(() => {
    abortStream();
    useChatStore.getState().cancel();
    latestRef.current.onSources?.([]);
  }, [abortStream]);

  const close = useCallback(() => {
    if (useChatStore.getState().isStreaming) {
      abortStream();
      useChatStore.getState().cancel();
    }
    useChatStore.getState().setOpen(false);
    latestRef.current.onSources?.([]);
  }, [abortStream]);

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
    abortStream();
    useChatStore.getState().clear();
    latestRef.current.onSources?.([]);
  }, [abortStream]);

  const setScopeOverride = useCallback((mode: ChatScopeMode) => {
    useChatStore.getState().setScopeOverride(mode);
  }, []);

  const activateCitation = useCallback((source: ChatSource) => {
    if (source.kind === 'web') {
      if (source.url) {
        window.open(source.url, '_blank', 'noopener,noreferrer');
      }
      return;
    }
    if (isFocusableSource(source)) {
      latestRef.current.onCitationActivate?.(source);
    }
  }, []);

  useEffect(() => abortStream, [abortStream]);

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