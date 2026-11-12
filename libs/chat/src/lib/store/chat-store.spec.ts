import { beforeEach, describe, expect, it } from 'vitest';

import type { ChatDoneEvent, ChatSource } from '@hermes/util-types';

import {
  buildHistory,
  stripCitations,
  useChatStore,
} from './chat-store';
import type { ChatMessage } from './chat-store';

const source: ChatSource = {
  kind: 'event',
  id: 'E1',
  event_id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
  title: 'Flooding in Valencia',
  url: null,
  source_name: null,
  published_at: null,
  retrieved_at: null,
  latitude: 39.47,
  longitude: -0.37,
  is_external: false,
  snippet: null,
};

const done: ChatDoneEvent = {
  type: 'done',
  provenance: {
    events: 1,
    articles: 0,
    timeline_nodes: 0,
    web: 0,
    background: false,
    grounding: [],
  },
  coverage: {
    level: 'sufficient',
    result_count: 1,
    best_semantic_similarity: 0.8,
    best_lexical_rank: 1,
    newest_age_hours: 2,
    recency_stale: false,
  },
  usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
  web_used: false,
  degraded: [],
};

function reset(): void {
  useChatStore.setState({
    messages: [],
    isOpen: false,
    scopeOverride: 'auto',
    isStreaming: false,
    activeId: null,
  });
}

function completedMessages(count: number): ChatMessage[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `message-${index}`,
    role: index % 2 === 0 ? 'user' : 'assistant',
    content: `message ${index} [E${index}]`,
    status: 'complete' as const,
    sources: [],
    done: null,
    error: null,
  }));
}

beforeEach(reset);

describe('chat store', () => {
  it('appends a user message and a streaming assistant placeholder', () => {
    const activeId = useChatStore.getState().send('  What happened?  ');

    const state = useChatStore.getState();
    expect(activeId).not.toBeNull();
    expect(state.messages).toHaveLength(2);
    expect(state.messages[0]).toMatchObject({
      role: 'user',
      content: 'What happened?',
      status: 'complete',
    });
    expect(state.messages[1]).toMatchObject({
      id: activeId,
      role: 'assistant',
      content: '',
      status: 'streaming',
    });
    expect(state.isStreaming).toBe(true);
  });

  it('ignores blank input and concurrent sends', () => {
    expect(useChatStore.getState().send('   ')).toBeNull();

    useChatStore.getState().send('question');
    expect(useChatStore.getState().send('second')).toBeNull();
    expect(useChatStore.getState().messages).toHaveLength(2);
  });

  it('builds a bounded history payload with citations stripped', () => {
    const history = buildHistory(completedMessages(20));

    expect(history).toHaveLength(16);
    expect(history[0]).toEqual({ role: 'user', content: 'message 4' });
    expect(history[15]).toEqual({ role: 'assistant', content: 'message 19' });
    expect(history.every((message) => !message.content.includes('[E'))).toBe(
      true,
    );
  });

  it('strips background and grouped citation markers', () => {
    expect(stripCitations('Fact [E1, A2] plus context [BG].')).toBe(
      'Fact plus context.',
    );
    expect(stripCitations('No citations here.')).toBe('No citations here.');
  });

  it('retries by replacing the last assistant response', () => {
    const firstId = useChatStore.getState().send('question');
    useChatStore.getState().applyEvent({ type: 'token', text: 'partial' });
    useChatStore.getState().applyEvent(done);

    const retryId = useChatStore.getState().retry();

    const state = useChatStore.getState();
    expect(retryId).not.toBeNull();
    expect(retryId).not.toBe(firstId);
    expect(state.messages).toHaveLength(2);
    expect(state.messages[1]).toMatchObject({
      id: retryId,
      content: '',
      status: 'streaming',
    });
    expect(state.isStreaming).toBe(true);
    expect(state.isOpen).toBe(true);
  });

  it('marks the active response cancelled and keeps partial text', () => {
    const activeId = useChatStore.getState().send('question');
    useChatStore.getState().applyEvent({ type: 'token', text: 'partial' });

    useChatStore.getState().cancel();

    const state = useChatStore.getState();
    expect(state.messages[1].id).toBe(activeId);
    expect(state.messages[1].content).toBe('partial');
    expect(state.messages[1].status).toBe('cancelled');
    expect(state.isStreaming).toBe(false);
    expect(state.activeId).toBeNull();
  });

  it('persists the scope override for the session', () => {
    useChatStore.getState().setScopeOverride('event');
    expect(useChatStore.getState().scopeOverride).toBe('event');

    useChatStore.getState().setScopeOverride('global');
    expect(useChatStore.getState().scopeOverride).toBe('global');
  });

  it('applies token, sources, and done events in order', () => {
    useChatStore.getState().send('question');

    useChatStore.getState().applyEvent({ type: 'token', text: 'Hello ' });
    useChatStore.getState().applyEvent({ type: 'token', text: 'world' });
    useChatStore.getState().applyEvent({
      type: 'sources',
      sources: [source],
    });
    useChatStore.getState().applyEvent(done);

    const message = useChatStore.getState().messages[1];
    expect(message.content).toBe('Hello world');
    expect(message.sources).toEqual([source]);
    expect(message.done).toEqual(done);
    expect(message.status).toBe('complete');
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it('applies a terminal error event', () => {
    useChatStore.getState().send('question');
    useChatStore.getState().applyEvent({
      type: 'error',
      code: 'MODEL_TIMEOUT',
      message: 'The answer model timed out.',
      retryable: true,
    });

    const message = useChatStore.getState().messages[1];
    expect(message.status).toBe('error');
    expect(message.error?.code).toBe('MODEL_TIMEOUT');
    expect(useChatStore.getState().isStreaming).toBe(false);
  });

  it('clears the conversation', () => {
    useChatStore.getState().send('question');
    useChatStore.getState().clear();

    expect(useChatStore.getState().messages).toEqual([]);
    expect(useChatStore.getState().activeId).toBeNull();
  });
});
