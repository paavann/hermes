import { create } from 'zustand';

import type {
  ChatDone,
  ChatError,
  ChatHistoryMessage,
  ChatStreamEvent,
  ChatSource,
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

const CITATION_PATTERN =
  /\[(?:BG|(?:E|A|T|W)\d+(?:\s*,\s*(?:E|A|T|W)\d+)*)\]/g;

let sequence = 0;

function createId(role: ChatMessage['role']): string {
  sequence += 1;
  return `${role}-${Date.now()}-${sequence}`;
}

function assistantMessage(): ChatMessage {
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
    .replace(CITATION_PATTERN, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\s+([.,!?;:])/g, '$1')
    .trim();
}

/** Build the bounded, citation-free history payload for the next request. */
export function buildHistory(messages: ChatMessage[]): ChatHistoryMessage[] {
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

function findLastUser(messages: ChatMessage[]): ChatMessage | null {
  let lastUser: ChatMessage | null = null;
  for (const message of messages) {
    if (message.role === 'user') {
      lastUser = message;
    }
  }
  return lastUser;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isOpen: false,
  scopeOverride: 'auto',
  isStreaming: false,
  activeId: null,

  setOpen: (isOpen) => set({ isOpen }),
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),
  setScopeOverride: (scopeOverride) => set({ scopeOverride }),

  send: (content) => {
    const trimmed = content.trim();
    if (!trimmed || get().isStreaming) {
      return null;
    }

    const assistant = assistantMessage();
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

    const lastUser = findLastUser(state.messages);
    if (!lastUser) {
      return null;
    }

    const assistant = assistantMessage();
    const messages = state.messages.filter(
      (message, index) =>
        index < state.messages.length - 1 || message.role === 'user',
    );

    set({
      messages: [...messages, assistant],
      isStreaming: true,
      activeId: assistant.id,
      isOpen: true,
    });
    return assistant.id;
  },

  cancel: () =>
    set((state) => ({
      messages: updateMessage(state.messages, state.activeId, (message) => ({
        ...message,
        status: 'cancelled',
      })),
      isStreaming: false,
      activeId: null,
    })),

  clear: () => set({ messages: [], isStreaming: false, activeId: null }),

  applyEvent: (event) => {
    const state = get();
    switch (event.type) {
      case 'status':
        return;
      case 'token':
        set({
          messages: updateMessage(state.messages, state.activeId, (message) => ({
            ...message,
            content: message.content + event.text,
          })),
        });
        return;
      case 'sources':
        set({
          messages: updateMessage(state.messages, state.activeId, (message) => ({
            ...message,
            sources: event.sources,
          })),
        });
        return;
      case 'done':
        set({
          messages: updateMessage(state.messages, state.activeId, (message) => ({
            ...message,
            status: 'complete',
            done: event,
            error: null,
          })),
          isStreaming: false,
          activeId: null,
        });
        return;
      case 'error':
        set({
          messages: updateMessage(state.messages, state.activeId, (message) => ({
            ...message,
            status: 'error',
            error: event,
          })),
          isStreaming: false,
          activeId: null,
        });
        return;
    }
  },

  fail: (error) =>
    set((state) => ({
      messages: updateMessage(state.messages, state.activeId, (message) => ({
        ...message,
        status: 'error',
        error,
      })),
      isStreaming: false,
      activeId: null,
    })),
}));
