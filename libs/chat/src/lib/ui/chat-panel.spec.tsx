import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type {
  ChatDoneEvent,
  ChatSource,
  ChatStreamEvent,
} from '@hermes/util-types';

import { ChatConfigProvider } from '../config-context';
import { useChatStore } from '../store/chat-store';
import type { ChatStreamFn } from '../hooks/use-chat';
import type { StreamChatOptions } from '../transport/sse';
import { ChatPanel } from './ChatPanel';
import type { ChatPanelProps } from './ChatPanel';

const eventSource: ChatSource = {
  kind: 'event',
  id: 'event-uuid',
  event_id: 'event-uuid',
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

const done: ChatDoneEvent = {
  type: 'done',
  provenance: {
    events: 1,
    articles: 1,
    timeline_nodes: 1,
    web: 1,
    background: true,
    grounding: [],
  },
  coverage: {
    level: 'sufficient',
    result_count: 3,
    best_semantic_similarity: 0.8,
    best_lexical_rank: 1,
    newest_age_hours: 2,
    recency_stale: false,
  },
  usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
  web_used: true,
  degraded: [],
};

interface DeferredTransport {
  stream: ChatStreamFn;
  calls: StreamChatOptions[];
  emit: (event: ChatStreamEvent) => void;
  finish: () => void;
}

function deferredTransport(): DeferredTransport {
  let options: StreamChatOptions | null = null;
  let resolve: (() => void) | null = null;
  const calls: StreamChatOptions[] = [];

  return {
    calls,
    stream: (next) => {
      calls.push(next);
      options = next;
      return new Promise<void>((complete) => {
        resolve = complete;
      });
    },
    emit: (event) => options?.onEvent(event),
    finish: () => {
      resolve?.();
      options = null;
    },
  };
}

function wrapper({ children }: { children: ReactNode }): React.JSX.Element {
  return (
    <ChatConfigProvider config={{ baseUrl: 'http://api.test', apiVer: 'v1' }}>
      {children}
    </ChatConfigProvider>
  );
}

function renderPanel(overrides: Partial<ChatPanelProps> = {}): ReturnType<
  typeof render
> & {
  onSources: ReturnType<typeof vi.fn>;
  onCitationActivate: ReturnType<typeof vi.fn>;
} {
  const onSources = vi.fn();
  const onCitationActivate = vi.fn();
  const result = render(
    <ChatPanel
      autoScope={{ eventId: null, viewport: null }}
      onSources={onSources}
      onCitationActivate={onCitationActivate}
      {...overrides}
    />,
    { wrapper },
  );
  return { ...result, onSources, onCitationActivate };
}

function openPanel(): void {
  fireEvent.click(screen.getByRole('button', { name: 'Open chat' }));
}

function sendQuestion(text: string): void {
  fireEvent.change(screen.getByLabelText('Chat message'), {
    target: { value: text },
  });
  fireEvent.keyDown(screen.getByLabelText('Chat message'), { key: 'Enter' });
}

function completeTurn(
  transport: DeferredTransport,
  events: ChatStreamEvent[],
): void {
  act(() => {
    for (const event of events) {
      transport.emit(event);
    }
    transport.finish();
  });
}

beforeEach(() => {
  useChatStore.setState({
    messages: [],
    isOpen: false,
    scopeOverride: 'auto',
    isStreaming: false,
    activeId: null,
  });
});

describe('ChatPanel', () => {
  it('dismisses to a rail and reopens', () => {
    renderPanel();

    expect(screen.queryByLabelText('Hermes chat')).toBeNull();
    openPanel();
    expect(screen.getByLabelText('Hermes chat')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Close chat' }));
    expect(screen.queryByLabelText('Hermes chat')).toBeNull();
    expect(screen.getByRole('button', { name: 'Open chat' })).toBeTruthy();
  });

  it('uses a solid, minimal panel chrome', () => {
    renderPanel();

    const rail = screen.getByTestId('chat-rail');
    expect(rail.className).toContain('w-12');
    expect(rail.className).toContain('bg-neutral-900');
    const openButton = screen.getByRole('button', { name: 'Open chat' });
    expect(openButton.querySelector('svg')).not.toBeNull();
    expect(openButton.className).toContain('hover:text-white');
    expect(openButton.className).not.toContain('hover:bg-');

    openPanel();

    const panel = screen.getByLabelText('Hermes chat');
    expect(panel.className).toContain('bg-neutral-900');
    expect(panel.className).not.toContain('bg-black');
    expect(screen.getByText('EXPLORE')).toBeTruthy();
    expect(screen.queryByText('HERMES // CHAT')).toBeNull();
    expect(document.querySelector('[class*="backdrop-blur"]')).toBeNull();
    expect(document.querySelector('[class*="bg-hud-bg/95"]')).toBeNull();
  });

  it('renders solid accent controls without a resolved scope readout', () => {
    renderPanel();
    openPanel();

    expect(
      screen.getByRole('button', { name: 'Clear conversation' }).className,
    ).toContain('bg-signal-teal');
    expect(
      screen.getByRole('button', { name: 'Close chat' }).className,
    ).toContain('bg-danger');

    expect(screen.getByRole('button', { name: 'auto' }).className).toContain(
      'bg-signal-teal',
    );
    expect(
      screen.getByRole('button', { name: 'viewport' }).className,
    ).not.toContain('bg-signal-teal');

    expect(screen.queryByText('GLOBAL')).toBeNull();
  });

  it('preserves the conversation across close and reopen', async () => {
    const transport = deferredTransport();
    renderPanel({ transport: transport.stream });
    openPanel();
    sendQuestion('What happened?');

    await waitFor(() => expect(transport.calls).toHaveLength(1));
    completeTurn(transport, [
      { type: 'token', text: 'Grounded answer.' },
      done,
    ]);
    await waitFor(() =>
      expect(screen.queryByTestId('streaming-cursor')).toBeNull(),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Close chat' }));
    openPanel();

    expect(screen.getByText('What happened?')).toBeTruthy();
    expect(screen.getByText('Grounded answer.')).toBeTruthy();
  });

  it('shows a streaming cursor and a stop control while streaming', async () => {
    const transport = deferredTransport();
    renderPanel({ transport: transport.stream });
    openPanel();
    sendQuestion('Question');

    await waitFor(() => expect(transport.calls).toHaveLength(1));
    expect(screen.getByTestId('streaming-cursor')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'STOP' }));
    expect(screen.queryByTestId('streaming-cursor')).toBeNull();
    expect(screen.getByText('CANCELLED')).toBeTruthy();
  });

  it('renders citation chips and forwards activation', async () => {
    const transport = deferredTransport();
    const { onCitationActivate } = renderPanel({ transport: transport.stream });
    openPanel();
    sendQuestion('Question');

    await waitFor(() => expect(transport.calls).toHaveLength(1));
    completeTurn(transport, [
      { type: 'token', text: 'Talks resumed [E1].' },
      { type: 'sources', sources: [eventSource] },
      done,
    ]);
    await waitFor(() =>
      expect(screen.queryByTestId('streaming-cursor')).toBeNull(),
    );

    const chip = screen.getByRole('button', {
      name: 'Open source: Ceasefire talks resume in Geneva',
    });
    fireEvent.click(chip);
    expect(onCitationActivate).toHaveBeenCalledWith(eventSource);
  });

  it('reports provenance and background usage in the footer', async () => {
    const transport = deferredTransport();
    renderPanel({ transport: transport.stream });
    openPanel();
    sendQuestion('Question');

    await waitFor(() => expect(transport.calls).toHaveLength(1));
    completeTurn(transport, [{ type: 'token', text: 'Answer [BG]' }, done]);
    await waitFor(() =>
      expect(screen.queryByTestId('streaming-cursor')).toBeNull(),
    );

    const footer = screen.getByTestId('provenance-footer').textContent ?? '';
    expect(footer).toContain('PLOTTED 3');
    expect(footer).toContain('WEB 1');
    expect(footer).toContain('BG YES');
  });

  it('shows a retry control after a terminal error', async () => {
    const transport = deferredTransport();
    renderPanel({ transport: transport.stream });
    openPanel();
    sendQuestion('Question');

    await waitFor(() => expect(transport.calls).toHaveLength(1));
    completeTurn(transport, [
      {
        type: 'error',
        code: 'MODEL_TIMEOUT',
        message: 'The answer model timed out.',
        retryable: true,
      },
    ]);
    await waitFor(() => expect(screen.getByText('MODEL_TIMEOUT')).toBeTruthy());

    fireEvent.click(screen.getByRole('button', { name: 'RETRY' }));
    await waitFor(() => expect(transport.calls).toHaveLength(2));
    expect(transport.calls[1].payload.message).toBe('Question');
    expect(screen.getByTestId('streaming-cursor')).toBeTruthy();
  });

  it('changes the request scope through the selector', async () => {
    const transport = deferredTransport();
    renderPanel({ transport: transport.stream });
    openPanel();
    sendQuestion('Question');

    await waitFor(() => expect(transport.calls).toHaveLength(1));
    completeTurn(transport, [done]);
    await waitFor(() => expect(transport.calls).toHaveLength(1));

    fireEvent.click(screen.getByRole('button', { name: 'viewport' }));
    expect(
      screen
        .getByRole('button', { name: 'viewport' })
        .getAttribute('aria-pressed'),
    ).toBe('true');
  });

  it('sends on Enter but not on Shift+Enter', async () => {
    const transport = deferredTransport();
    renderPanel({ transport: transport.stream });
    openPanel();

    const input = screen.getByLabelText('Chat message');
    fireEvent.change(input, { target: { value: 'Question' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });

    expect(transport.calls).toHaveLength(0);
    expect((input as HTMLTextAreaElement).value).toBe('Question');

    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(transport.calls).toHaveLength(1));
    expect(transport.calls[0].payload.message).toBe('Question');
  });
});
