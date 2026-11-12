import { describe, expect, it, vi } from 'vitest';

import type { ChatRequest, ChatStreamEvent } from '@hermes/util-types';

import {
  ChatTransportError,
  chatErrorFromTransport,
  parseSseStream,
  streamChat,
} from './sse';

const payload: ChatRequest = {
  message: 'What happened?',
  scope: { type: 'global' },
};

function streamResponse(
  chunks: string[],
  init: ResponseInit = {},
): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { 'content-type': 'text/event-stream' },
    ...init,
  });
}

async function collect(chunks: string[]): Promise<ChatStreamEvent[]> {
  const body = streamResponse(chunks).body;
  if (body === null) {
    throw new Error('test response has no body');
  }
  const events: ChatStreamEvent[] = [];
  for await (const event of parseSseStream(body)) {
    events.push(event);
  }
  return events;
}

describe('SSE parser', () => {
  it('parses frames split across arbitrary chunk boundaries', async () => {
    const events = await collect([
      'event: status\r\ndata: {"type":"status","stage":"accepted"}\r\n\r\n',
      'event: token\r\ndata: {"type":"token","text":"Hel',
      'lo"}\r\n\r\n',
    ]);

    expect(events).toEqual([
      { type: 'status', stage: 'accepted' },
      { type: 'token', text: 'Hello' },
    ]);
  });

  it('joins multi-line data fields and ignores comments', async () => {
    const events = await collect([
      ': keepalive\n\n',
      'event: done\ndata: {"type":"done",\ndata: "provenance":{"events":1,' +
        '"articles":0,"timeline_nodes":0,"web":0,"background":false,' +
        '"grounding":[]},"coverage":{"level":"empty","result_count":0,' +
        '"best_semantic_similarity":null,"best_lexical_rank":null,' +
        '"newest_age_hours":null,"recency_stale":false},"usage":null,' +
        '"web_used":false,"degraded":[]}\n\n',
    ]);

    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('done');
  });

  it('drops unknown event types and mismatched event names', async () => {
    const events = await collect([
      'event: token\ndata: {"type":"status","stage":"accepted"}\n\n',
      'event: future\ndata: {"type":"future","value":1}\n\n',
      'event: token\ndata: {"type":"token","text":"ok"}\n\n',
    ]);

    expect(events).toEqual([{ type: 'token', text: 'ok' }]);
  });

  it('flushes a final frame without a trailing blank line', async () => {
    const events = await collect([
      'event: token\ndata: {"type":"token","text":"tail"}',
    ]);

    expect(events).toEqual([{ type: 'token', text: 'tail' }]);
  });

  it('rejects malformed JSON', async () => {
    await expect(
      collect(['event: token\ndata: not-json\n\n']),
    ).rejects.toBeInstanceOf(ChatTransportError);
  });
});

describe('streamChat', () => {
  it('posts JSON and forwards every event', async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
      streamResponse([
        'event: status\ndata: {"type":"status","stage":"accepted"}\n\n',
        'event: error\ndata: {"type":"error","code":"MODEL_FAILED",' +
          '"message":"failed","retryable":true}\n\n',
      ]),
    );
    const events: ChatStreamEvent[] = [];

    await streamChat({
      url: 'http://api.test/chat',
      payload,
      onEvent: (event) => events.push(event),
      fetchImpl,
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      'http://api.test/chat',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    );
    expect(events.map((event) => event.type)).toEqual(['status', 'error']);
  });

  it('surfaces JSON error envelopes with Retry-After', async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          err_code: 'CHAT_BUSY',
          err_msg: 'All streams are busy.',
          details: {},
        }),
        {
          status: 503,
          headers: {
            'content-type': 'application/json',
            'retry-after': '2',
          },
        },
      ),
    );

    await expect(
      streamChat({
        url: 'http://api.test/chat',
        payload,
        onEvent: () => undefined,
        fetchImpl,
      }),
    ).rejects.toMatchObject({
      code: 'CHAT_BUSY',
      message: 'All streams are busy.',
      status: 503,
      retryAfter: 2,
      retryable: true,
    });
  });

  it('rethrows abort errors unchanged', async () => {
    const controller = new AbortController();
    controller.abort();
    const abortError = new DOMException('Aborted', 'AbortError');
    const fetchImpl = vi.fn<typeof fetch>().mockRejectedValue(abortError);

    await expect(
      streamChat({
        url: 'http://api.test/chat',
        payload,
        signal: controller.signal,
        onEvent: () => undefined,
        fetchImpl,
      }),
    ).rejects.toBe(abortError);
  });

  it('rejects when the stream ends without a terminal event', async () => {
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        streamResponse([
          'event: status\ndata: {"type":"status","stage":"accepted"}\n\n',
        ]),
      );

    await expect(
      streamChat({
        url: 'http://api.test/chat',
        payload,
        onEvent: () => undefined,
        fetchImpl,
      }),
    ).rejects.toMatchObject({
      code: 'INTERNAL_ERROR',
      retryable: true,
    });
  });

  it('maps unknown transport codes to INTERNAL_ERROR', () => {
    const error = new ChatTransportError('nope', {
      status: 500,
      code: 'SOMETHING_ELSE',
      retryAfter: null,
      retryable: true,
    });

    expect(chatErrorFromTransport(error)).toEqual({
      code: 'INTERNAL_ERROR',
      message: 'nope',
      retryable: true,
    });
  });
});
