import type {
  ChatError,
  ChatErrorCode,
  ChatRequest,
  ChatStreamEvent,
} from '@hermes/util-types';

export interface SseMessage {
  event: string;
  data: string;
}

export interface ChatTransportErrorInit {
  status: number;
  code: string;
  retryAfter: number | null;
  retryable: boolean;
}

export class ChatTransportError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryAfter: number | null;
  readonly retryable: boolean;

  constructor(message: string, init: ChatTransportErrorInit) {
    super(message);
    this.name = 'ChatTransportError';
    this.status = init.status;
    this.code = init.code;
    this.retryAfter = init.retryAfter;
    this.retryable = init.retryable;
  }
}

export interface StreamChatOptions {
  url: string;
  payload: ChatRequest;
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
  fetchImpl?: typeof fetch;
}

interface ErrorEnvelope {
  err_code?: string;
  err_msg?: string;
  details?: unknown;
}

const EVENT_TYPES: ReadonlySet<string> = new Set([
  'status',
  'token',
  'sources',
  'done',
  'error',
]);

const TERMINAL_TYPES: ReadonlySet<string> = new Set(['done', 'error']);

const EVENT_SEPARATOR = /\r?\n\r?\n/;
const LINE_BREAK = /\r\n|\n|\r/;
const MAX_BUFFER_CHARS = 1_000_000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isChatStreamEvent(value: unknown): value is ChatStreamEvent {
  return (
    isRecord(value) &&
    typeof value.type === 'string' &&
    EVENT_TYPES.has(value.type)
  );
}

function toErrorEnvelope(value: unknown): ErrorEnvelope {
  if (!isRecord(value)) {
    return {};
  }
  return {
    err_code: typeof value.err_code === 'string' ? value.err_code : undefined,
    err_msg: typeof value.err_msg === 'string' ? value.err_msg : undefined,
    details: value.details,
  };
}

function parseBlock(block: string): SseMessage | null {
  let event = 'message';
  const data: string[] = [];

  for (const line of block.split(LINE_BREAK)) {
    if (!line || line.startsWith(':')) {
      continue;
    }
    const separator = line.indexOf(':');
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? '' : line.slice(separator + 1);
    if (value.startsWith(' ')) {
      value = value.slice(1);
    }

    if (field === 'event') {
      event = value;
    } else if (field === 'data') {
      data.push(value);
    }
  }

  if (data.length === 0) {
    return null;
  }
  return { event, data: data.join('\n') };
}

function decodeEvent(message: SseMessage): ChatStreamEvent | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(message.data);
  } catch {
    throw new ChatTransportError('The chat stream returned malformed data.', {
      status: 0,
      code: 'INTERNAL_ERROR',
      retryAfter: null,
      retryable: true,
    });
  }

  if (!isChatStreamEvent(parsed)) {
    return null;
  }
  if (message.event !== 'message' && message.event !== parsed.type) {
    return null;
  }
  return parsed;
}

function retryAfterSeconds(response: Response): number | null {
  const header = response.headers.get('retry-after');
  if (!header) {
    return null;
  }
  const seconds = Number.parseInt(header, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

async function responseError(response: Response): Promise<ChatTransportError> {
  let envelope: ErrorEnvelope = {};
  try {
    envelope = toErrorEnvelope(await response.json());
  } catch {
    // Fall back to the HTTP status when the body is not JSON.
  }

  return new ChatTransportError(
    envelope.err_msg ?? `The chat request failed with status ${response.status}.`,
    {
      status: response.status,
      code: envelope.err_code ?? 'HTTP_ERROR',
      retryAfter: retryAfterSeconds(response),
      retryable: response.status >= 500 || response.status === 429,
    },
  );
}

export async function* parseSseStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<ChatStreamEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });

      if (buffer.length > MAX_BUFFER_CHARS) {
        throw new ChatTransportError('The chat stream exceeded its buffer.', {
          status: 0,
          code: 'INTERNAL_ERROR',
          retryAfter: null,
          retryable: true,
        });
      }

      let match = EVENT_SEPARATOR.exec(buffer);
      while (match) {
        const block = buffer.slice(0, match.index);
        buffer = buffer.slice(match.index + match[0].length);
        const message = parseBlock(block);
        if (message) {
          const event = decodeEvent(message);
          if (event) {
            yield event;
          }
        }
        match = EVENT_SEPARATOR.exec(buffer);
      }

      if (done) {
        const message = parseBlock(buffer);
        if (message) {
          const event = decodeEvent(message);
          if (event) {
            yield event;
          }
        }
        return;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

const ERROR_CODES: ReadonlySet<string> = new Set([
  'RETRIEVAL_FAILED',
  'MODEL_TIMEOUT',
  'STREAM_TIMEOUT',
  'MODEL_FAILED',
  'INTERNAL_ERROR',
  'CHAT_BUSY',
]);

function isChatErrorCode(value: string): value is ChatErrorCode {
  return ERROR_CODES.has(value);
}

export function chatErrorFromTransport(
  error: ChatTransportError,
): ChatError {
  return {
    code: isChatErrorCode(error.code) ? error.code : 'INTERNAL_ERROR',
    message: error.message,
    retryable: error.retryable,
  };
}

export async function streamChat({
  url,
  payload,
  signal,
  onEvent,
  fetchImpl,
}: StreamChatOptions): Promise<void> {
  const request = fetchImpl ?? fetch;
  let response: Response;
  try {
    response = await request(url, {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }
    throw new ChatTransportError(
      error instanceof Error ? error.message : 'The chat request failed.',
      {
        status: 0,
        code: 'INTERNAL_ERROR',
        retryAfter: null,
        retryable: true,
      },
    );
  }

  if (!response.ok) {
    throw await responseError(response);
  }
  if (!response.body) {
    throw new ChatTransportError('The chat response had no stream body.', {
      status: response.status,
      code: 'INTERNAL_ERROR',
      retryAfter: null,
      retryable: true,
    });
  }

  let terminal = false;
  for await (const event of parseSseStream(response.body)) {
    if (TERMINAL_TYPES.has(event.type)) {
      terminal = true;
    }
    onEvent(event);
  }

  if (!terminal && !signal?.aborted) {
    throw new ChatTransportError(
      'The chat stream ended unexpectedly.',
      {
        status: response.status,
        code: 'INTERNAL_ERROR',
        retryAfter: null,
        retryable: true,
      },
    );
  }
}
