import { create } from 'zustand';
import type {
  ChatDone,
  ChatError,
  ChatHistoryMessage,
  ChatSource,
  ChatStreamEvent,
} from '@hermes/util-types';

export type ChatScopeMode = 'auto' | 'event' | 'viewport' | 'global';
export type ChatMessageStatus = 'streaming' | 'complete' | 'error' | 'cancelled';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status: ChatMessageStatus;
  sources: ChatSource[];
  done: ChatDone | null;
  error: ChatError | null;
}

export interface ChatState {
  messages: ChatMessage[];
  isOpen: boolean;
  scopeOverride: ChatScopeMode;
  isStreaming: boolean;
  activeId: string | null;
  setOpen: (open: boolean) => void;
  toggleOpen: () => void;
  setScopeOverride: (mode: ChatScopeMode) => void;
  send: (content: string) => string | null;
  retry: () => string | null;
  cancel: () => void;
  clear: () => void;
  applyEvent: (event: ChatStreamEvent) => void;
  fail: (error: ChatError) => void;
}

export const MAX_HISTORY_MESSAGES = 16;
export const MAX_HISTORY_CONTENT = 8000;

export const CITATION_MARKER_PATTERN =
  /\[((?:BG|[EATW]\d+)(?:\s*,\s*(?:BG|[EATW]\d+))*)\]/gi;

export const INITIAL_CHAT_STATE = {
  messages: [] as ChatMessage[],
  isOpen: false,
  scopeOverride: 'auto' as ChatScopeMode,
  isStreaming: false,
  activeId: null as string | null,
};

let sequence = 0;

function createId(role: ChatMessage['role']): string {
  sequence += 1;
  return `${role}-${Date.now()}-${sequence}`;
}

function createAssistantMessage(): ChatMessage {
  return {
    id: createId('assistant'),
    role: 'assistant',
    content: '',
    status: 'streaming',
    sources: [],
    done: null,
    error: null,
  };
}

/** Remove inline citation markers so stale IDs never leak into request history. */
export function stripCitations(content: string): string {
  return content
    .replace(CITATION_MARKER_PATTERN, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\s+([.,!?;:])/g, '$1')
    .trim();
}

/** Build the bounded, citation-free history payload for the next request. */
export function buildHistory(
  messages: readonly ChatMessage[],
): ChatHistoryMessage[] {
  return messages
    .filter(
      (message) =>
        message.status !== 'streaming' && message.content.trim().length > 0,
    )
    .slice(-MAX_HISTORY_MESSAGES)
    .map((message) => ({
      role: message.role,
      content: stripCitations(message.content).slice(0, MAX_HISTORY_CONTENT),
    }))
    .filter((message) => message.content.length > 0);
}

export function findLastUserIndex(messages: readonly ChatMessage[]): number {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === 'user') {
      return index;
    }
  }
  return -1;
}

function updateMessage(
  messages: ChatMessage[],
  activeId: string | null,
  update: (message: ChatMessage) => ChatMessage,
): ChatMessage[] {
  if (activeId === null) {
    return messages;
  }
  return messages.map((message) =>
    message.id === activeId ? update(message) : message,
  );
}

export const useChatStore = create<ChatState>((set, get) => {
  const updateActive = (
    updater: (message: ChatMessage) => ChatMessage,
    storePatch: Partial<ChatState> = {},
  ): void => {
    set((state) => ({
      ...storePatch,
      messages: updateMessage(state.messages, state.activeId, updater),
    }));
  };

  const failActive = (error: ChatError): void => {
    updateActive(
      (message) => ({ ...message, status: 'error', error }),
      { isStreaming: false, activeId: null },
    );
  };

  return {
    ...INITIAL_CHAT_STATE,

    setOpen: (isOpen) => set({ isOpen }),
    toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),
    setScopeOverride: (scopeOverride) => set({ scopeOverride }),

    send: (content) => {
      const trimmed = content.trim();
      if (!trimmed || get().isStreaming) {
        return null;
      }
      const assistant = createAssistantMessage();
      set((state) => ({
        messages: [
          ...state.messages,
          {
            id: createId('user'),
            role: 'user',
            content: trimmed,
            status: 'complete',
            sources: [],
            done: null,
            error: null,
          },
          assistant,
        ],
        isStreaming: true,
        activeId: assistant.id,
      }));
      return assistant.id;
    },

    retry: () => {
      const state = get();
      if (state.isStreaming) {
        return null;
      }
      const lastUserIdx = findLastUserIndex(state.messages);
      if (lastUserIdx < 0) {
        return null;
      }
      const assistant = createAssistantMessage();
      set({
        messages: [...state.messages.slice(0, lastUserIdx + 1), assistant],
        isStreaming: true,
        activeId: assistant.id,
        isOpen: true,
      });
      return assistant.id;
    },

    cancel: () => {
      updateActive(
        (message) => ({ ...message, status: 'cancelled' }),
        { isStreaming: false, activeId: null },
      );
    },

    clear: () => set({ messages: [], isStreaming: false, activeId: null }),

    applyEvent: (event) => {
      switch (event.type) {
        case 'status':
          return;
        case 'token':
          updateActive((message) => ({
            ...message,
            content: message.content + event.text,
          }));
          return;
        case 'sources':
          updateActive((message) => ({
            ...message,
            sources: event.sources,
          }));
          return;
        case 'done':
          updateActive(
            (message) => ({
              ...message,
              status: 'complete',
              done: event,
              error: null,
            }),
            { isStreaming: false, activeId: null },
          );
          return;
        case 'error':
          failActive({
            code: event.code,
            message: event.message,
            retryable: event.retryable,
          });
          return;
      }
    },

    fail: failActive,
  };
});