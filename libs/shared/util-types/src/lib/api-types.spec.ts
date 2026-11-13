import { describe, expect, it } from 'vitest';

import type {
  ChatDoneEvent,
  ChatErrorEvent,
  ChatEventScope,
  ChatGlobalScope,
  ChatRequest,
  ChatSource,
  ChatSourcesEvent,
  ChatStatusEvent,
  ChatStreamEvent,
  ChatTokenEvent,
  ChatViewportScope,
} from './api-types.js';

import doneFixture from '../../fixtures/chat/done.json';
import errorFixture from '../../fixtures/chat/error.json';
import globalRequestFixture from '../../fixtures/chat/request-global.json';
import eventRequestFixture from '../../fixtures/chat/request-event.json';
import requestFixture from '../../fixtures/chat/request.json';
import sourcesFixture from '../../fixtures/chat/sources.json';
import statusFixture from '../../fixtures/chat/status.json';
import tokenFixture from '../../fixtures/chat/token.json';

const viewportScope: ChatViewportScope = {
  type: 'viewport',
  bbox: { north: 60, south: 30, east: 60, west: 20 },
};

const eventScope: ChatEventScope = {
  type: 'event',
  event_id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
};

const globalScope: ChatGlobalScope = { type: 'global' };

const request: ChatRequest = {
  message: 'What changed in the ceasefire talks this week?',
  history: [
    { role: 'user', content: 'What is happening in the region?' },
    { role: 'assistant', content: 'Talks resumed on Tuesday [E1].' },
  ],
  scope: viewportScope,
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
  snippet: 'Delegations met on Tuesday.',
};

const articleSource: ChatSource = {
  kind: 'article',
  id: 'A1',
  event_id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
  title: 'Talks resume',
  url: 'https://example.com/talks',
  source_name: 'Example News',
  published_at: '2026-11-07T10:00:00Z',
  retrieved_at: null,
  latitude: null,
  longitude: null,
  is_external: false,
  snippet: 'Negotiators returned to the table.',
};

const timelineSource: ChatSource = {
  kind: 'timeline',
  id: 'T1',
  event_id: null,
  title: '2024 ceasefire',
  url: null,
  source_name: null,
  published_at: null,
  retrieved_at: null,
  latitude: null,
  longitude: null,
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
  snippet: 'A weekly roundup.',
};

const status: ChatStatusEvent = { type: 'status', stage: 'accepted' };
const token: ChatTokenEvent = {
  type: 'token',
  text: 'Talks resumed on Tuesday ',
};
const sources: ChatSourcesEvent = {
  type: 'sources',
  sources: [eventSource, articleSource, timelineSource, webSource],
};
const done: ChatDoneEvent = {
  type: 'done',
  provenance: {
    events: 1,
    articles: 1,
    timeline_nodes: 1,
    web: 1,
    background: false,
    grounding: [],
  },
  coverage: {
    level: 'sufficient',
    result_count: 3,
    best_semantic_similarity: 0.82,
    best_lexical_rank: 1,
    newest_age_hours: 2.5,
    recency_stale: false,
  },
  usage: { prompt_tokens: 900, completion_tokens: 120, total_tokens: 1020 },
  web_used: true,
  degraded: ['planner_fallback'],
};
const error: ChatErrorEvent = {
  type: 'error',
  code: 'MODEL_TIMEOUT',
  message: 'The answer model timed out.',
  retryable: true,
};

function describeEvent(event: ChatStreamEvent): string {
  switch (event.type) {
    case 'status':
      return `status:${event.stage}`;
    case 'token':
      return `token:${event.text.trim()}`;
    case 'sources':
      return `sources:${event.sources.map((source) => source.kind).join(',')}`;
    case 'done':
      return `done:${event.coverage.level}`;
    case 'error':
      return `error:${event.code}`;
  }
}

describe('chat contract fixtures', () => {
  it('accepts the shared viewport request', () => {
    expect(requestFixture).toEqual(request);
  });

  it('accepts the shared event and global requests', () => {
    expect(eventRequestFixture.scope).toEqual(eventScope);
    expect(globalRequestFixture.scope).toEqual(globalScope);
  });

  it('accepts the shared status and token events', () => {
    expect(statusFixture).toEqual(status);
    expect(tokenFixture).toEqual(token);
  });

  it('accepts the shared sources event with every source kind', () => {
    expect(sourcesFixture).toEqual(sources);
  });

  it('accepts the shared done event', () => {
    expect(doneFixture).toEqual(done);
  });

  it('accepts the shared error event', () => {
    expect(errorFixture).toEqual(error);
  });

  it('narrows every event variant through the discriminated union', () => {
    const events: ChatStreamEvent[] = [
      status,
      token,
      sources,
      done,
      error,
    ];

    expect(events.map(describeEvent)).toEqual([
      'status:accepted',
      'token:Talks resumed on Tuesday',
      'sources:event,article,timeline,web',
      'done:sufficient',
      'error:MODEL_TIMEOUT',
    ]);
  });
});
