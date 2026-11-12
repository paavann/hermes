import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type {
  ChatBoundingBox,
  ChatDoneEvent,
  ChatSource,
  ChatStreamEvent,
} from '@hermes/util-types';

import { ChatConfigProvider } from '../config-context';
import { useChatStore } from '../store/chat-store';
import { useChat, resolveScope } from './use-chat';
import type { AutoScope, ChatStreamFn } from './use-chat';
import type { StreamChatOptions } from '../transport/sse';

const viewport: ChatBoundingBox = {
  north: 60,
  south: 30,
  east: 60,
  west: 20,
};

const eventSource: ChatSource = {
  kind: 'event',
  id: 'E1',
  event_id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
  title: 'Ceasefire talks resume in Geneva',
  url: null,
  source_name: null,
  published_at: null,
  retrieved_at: null,
  latitude: 46.2044,
  longitude: 6.1432,
  is_external: false,
  snippet: null,
};

const webSource: ChatSource = {
  kind: 'web',
  id: 'W1',
  event_id: null,
  title: 'Regional update',
  url: 'https://news.example.com/update',
  source_name: 'news.example.com',
  published_at: null,
  retrieved_at: '2026-11-08T09:00:00Z',
  latitude: null,
  longitude: null,
  is_external: true,
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

const autoScope: AutoScope = {
  eventId: eventSource.event_id,
  viewport,
};

function wrapper({ children }: { children: ReactNode }): React.JSX.Element {
  return (
    <ChatConfigProvider config={{ baseUrl: 'http://api.test', apiVer: 'v1' }}>
      {children}
    </ChatConfigProvider>
  );
}

function createTransport(
  events: ChatStreamEvent[] = [
    { type: 'status', stage: 'accepted' },
    { type: 'token', text: 'Grounded answer [E1].' },
    { type: 'sources', sources: [eventSource] },
    done,
  ],
): { stream: ChatStreamFn; calls: StreamChatOptions[] } {
  const calls: StreamChatOptions[] = [];
  const stream: ChatStreamFn = (options) => {
    calls.push(options);
    for (const event of events) {
      options.onEvent(event);
    }
    return Promise.resolve();
  };
  return { stream, calls };
}

function resetStore(): void {
  useChatStore.setState({
    messages: [],
    isOpen: false,
    scopeOverride: 'auto',
    isStreaming: false,
    activeId: null,
  });
}

beforeEach(resetStore);

describe('resolveScope', () => {
  it('prefers the selected event in auto mode', () => {
    expect(resolveScope('auto', autoScope)).toEqual({
      type: 'event',
      event_id: eventSource.event_id,
    });
  });

  it('falls back from auto mode to the viewport and then global', () => {
    expect(resolveScope('auto', { eventId: null, viewport })).toEqual({
      type: 'viewport',
      bbox: viewport,
    });
    expect(resolveScope('auto', { eventId: null, viewport: null })).toEqual({
      type: 'global',
    });
  });

  it('honors explicit viewport and global modes', () => {
    expect(resolveScope('viewport', autoScope)).toEqual({
      type: 'viewport',
      bbox: viewport,
    });
    expect(resolveScope('global', autoScope)).toEqual({ type: 'global' });
  });

  it('downgrades unavailable explicit modes', () => {
    expect(resolveScope('event', { eventId: null, viewport })).toEqual({
      type: 'viewport',
      bbox: viewport,
    });
    expect(resolveScope('event', { eventId: null, viewport: null })).toEqual({
      type: 'global',
    });
    expect(resolveScope('viewport', { eventId: null, viewport: null })).toEqual(
      { type: 'global' },
    );
  });
});

describe('useChat', () => {
  it('sends history and the resolved scope, then applies the stream', async () => {
    const { stream, calls } = createTransport();
    const { result } = renderHook(
      () => useChat({ autoScope, transport: stream }),
      { wrapper },
    );

    act(() => {
      result.current.send('What changed?');
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('http://api.test/api/v1/chat');
    expect(calls[0].payload).toEqual({
      message: 'What changed?',
      history: [],
      scope: { type: 'event', event_id: eventSource.event_id },
    });
    expect(result.current.messages[1]).toMatchObject({
      content: 'Grounded answer [E1].',
      status: 'complete',
      sources: [eventSource],
    });
  });

  it('includes earlier completed messages as citation-free history', async () => {
    const { stream, calls } = createTransport();
    const { result } = renderHook(
      () => useChat({ autoScope, transport: stream }),
      { wrapper },
    );

    act(() => {
      result.current.send('first question');
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    act(() => {
      result.current.send('second question');
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(calls[1].payload.history).toEqual([
      { role: 'user', content: 'first question' },
      { role: 'assistant', content: 'Grounded answer.' },
    ]);
  });

  it('retries the last user message without duplicating it', async () => {
    const { stream, calls } = createTransport();
    const { result } = renderHook(
      () => useChat({ autoScope, transport: stream }),
      { wrapper },
    );

    act(() => {
      result.current.send('question');
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    act(() => {
      result.current.retry();
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(calls[1].payload.message).toBe('question');
    expect(calls[1].payload.history).toEqual([]);
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].status).toBe('complete');
  });

  it('aborts the active request when cancelled', async () => {
    let captured: StreamChatOptions | null = null;
    type Resolver = () => void;
    let resolveStream: Resolver = () => undefined;
    const stream: ChatStreamFn = (options) => {
      captured = options;
      return new Promise<void>((resolve) => {
        resolveStream = resolve;
      });
    };
    const { result } = renderHook(() => useChat({ autoScope, transport: stream }), {
      wrapper,
    });

    act(() => {
      result.current.send('question');
    });
    await waitFor(() => expect(captured).not.toBeNull());

    act(() => {
      result.current.cancel();
    });

    const request = captured as StreamChatOptions | null;
    expect(request?.signal?.aborted).toBe(true);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages[1].status).toBe('cancelled');
    resolveStream();
  });

  it('aborts an active request and closes the panel', async () => {
    let captured: StreamChatOptions | null = null;
    const stream: ChatStreamFn = (options) => {
      captured = options;
      return new Promise<void>(() => undefined);
    };
    const { result } = renderHook(() => useChat({ autoScope, transport: stream }), {
      wrapper,
    });

    act(() => {
      result.current.open();
      result.current.send('question');
    });
    await waitFor(() => expect(captured).not.toBeNull());

    act(() => {
      result.current.close();
    });

    const request = captured as StreamChatOptions | null;
    expect(request?.signal?.aborted).toBe(true);
    expect(result.current.isOpen).toBe(false);
    expect(result.current.messages[1].status).toBe('cancelled');
  });

  it('notifies source subscribers and clears them on close', async () => {
    const { stream } = createTransport();
    const onSources = vi.fn();
    const { result } = renderHook(
      () => useChat({ autoScope, transport: stream, onSources }),
      { wrapper },
    );

    act(() => {
      result.current.open();
      result.current.send('question');
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(onSources).toHaveBeenCalledWith([eventSource]);
    onSources.mockClear();

    act(() => {
      result.current.close();
    });

    expect(onSources).toHaveBeenCalledWith([]);
  });

  it('opens web citations and forwards plotted citations', () => {
    const onCitationActivate = vi.fn();
    const openSpy = vi
      .spyOn(window, 'open')
      .mockImplementation(() => null);
    const { stream } = createTransport();
    const { result } = renderHook(
      () => useChat({ autoScope, transport: stream, onCitationActivate }),
      { wrapper },
    );

    act(() => {
      result.current.activateCitation(webSource);
    });
    expect(openSpy).toHaveBeenCalledWith(
      'https://news.example.com/update',
      '_blank',
      'noopener,noreferrer',
    );

    act(() => {
      result.current.activateCitation(eventSource);
    });
    expect(onCitationActivate).toHaveBeenCalledWith(eventSource);

    act(() => {
      result.current.activateCitation({
        ...eventSource,
        latitude: null,
        longitude: null,
      });
    });
    expect(onCitationActivate).toHaveBeenCalledTimes(1);

    openSpy.mockRestore();
  });

  it('maps transport failures to a retryable error message', async () => {
    const stream: ChatStreamFn = () =>
      Promise.reject(new Error('network down'));
    const { result } = renderHook(() => useChat({ autoScope, transport: stream }), {
      wrapper,
    });

    act(() => {
      result.current.send('question');
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(result.current.messages[1]).toMatchObject({
      status: 'error',
      error: {
        code: 'INTERNAL_ERROR',
        message: 'network down',
        retryable: true,
      },
    });
  });

  it('sets, persists, and clears the conversation', async () => {
    const { stream } = createTransport();
    const { result } = renderHook(
      () => useChat({ autoScope, transport: stream }),
      { wrapper },
    );

    act(() => {
      result.current.setScopeOverride('global');
    });
    expect(result.current.scopeMode).toBe('global');
    expect(result.current.scope).toEqual({ type: 'global' });

    act(() => {
      result.current.send('question');
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(result.current.messages).toHaveLength(2);

    act(() => {
      result.current.clear();
    });
    expect(result.current.messages).toEqual([]);
  });
});
