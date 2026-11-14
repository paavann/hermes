import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type {
  ChatDone,
  ChatError,
  ChatSource,
  ChatStage,
  ChatStreamEvent,
} from '@hermes/util-types';

export type ChatScopeMode = 'auto' | 'event' | 'viewport' | 'global';
export type ChatMessageStatus = 'streaming' | 'complete' | 'error' | 'cancelled';

const CHAT_STAGES = [
  'accepted',
  'planning',
  'retrieving',
  'searching',
  'generating',
  'finalizing',
] as const satisfies readonly ChatStage[];

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status: ChatMessageStatus;
  stage: ChatStage | null;
  sources: ChatSource[];
  done: ChatDone | null;
  error: ChatError | null;
}

export interface ChatState {
  messages: ChatMessage[];
  threadId: string;
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

interface ChatPersistedState {
  threadId: string;
  messages: PersistedChatMessage[];
}

function fallbackUuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16);
    const value = char === 'x' ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

export function createThreadId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return fallbackUuid();
}

export const INITIAL_CHAT_STATE = {
  messages: [] as ChatMessage[],
  threadId: createThreadId(),
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
    stage: null,
    sources: [],
    done: null,
    error: null,
  };
}

export function findLastUserIndex(messages: readonly ChatMessage[]): number {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === 'user') {
      return index;
    }
  }
  return -1;
}

type PersistedChatMessage = Omit<ChatMessage, 'stage'> & {
  stage?: ChatStage | null;
};

function isChatStage(value: unknown): value is ChatStage {
  return CHAT_STAGES.some((stage) => stage === value);
}

function isPersistedMessage(value: unknown): value is PersistedChatMessage {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  return (
    'id' in value &&
    typeof value.id === 'string' &&
    'role' in value &&
    (value.role === 'user' || value.role === 'assistant') &&
    'content' in value &&
    typeof value.content === 'string' &&
    'status' in value &&
    typeof value.status === 'string' &&
    (!('stage' in value) || value.stage === null || isChatStage(value.stage)) &&
    'sources' in value &&
    Array.isArray(value.sources) &&
    'done' in value &&
    'error' in value
  );
}

function isPersistedState(value: unknown): value is ChatPersistedState {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  return (
    'threadId' in value &&
    typeof value.threadId === 'string' &&
    'messages' in value &&
    Array.isArray(value.messages)
  );
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

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => {
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
          (message) => ({ ...message, status: 'error', error, stage: null }),
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
                stage: null,
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
            (message) => ({ ...message, status: 'cancelled', stage: null }),
            { isStreaming: false, activeId: null },
          );
        },

        clear: () =>
          set({
            messages: [],
            threadId: createThreadId(),
            isStreaming: false,
            activeId: null,
          }),

        applyEvent: (event) => {
          switch (event.type) {
            case 'status':
              updateActive((message) => ({ ...message, stage: event.stage }));
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
                  stage: null,
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
    },
    {
      name: 'hermes-chat',
      version: 1,
      storage: createJSONStorage<ChatPersistedState>(() => localStorage),
      partialize: (state) => ({
        threadId: state.threadId,
        messages: state.messages,
      }),
      merge: (persisted, current) => {
        if (!isPersistedState(persisted)) {
          return current;
        }
        return {
          ...current,
          threadId: persisted.threadId || current.threadId,
          messages: persisted.messages
            .filter(isPersistedMessage)
            .map((message) => ({
              ...message,
              stage: isChatStage(message.stage) ? message.stage : null,
              status:
                message.status === 'streaming'
                  ? ('cancelled' as const)
                  : message.status,
            })),
        };
      },
      skipHydration: true,
    },
  ),
);
