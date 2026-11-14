import type { ChatRequest, ChatStreamEvent } from "@hermes/util-types"

export interface SseMessage {
  event: string
  data: string
}

export interface ChatTransportErrInit {
  status: number
  code: string
  retryAfter: number | null
  retryable: boolean
}

export interface StreamChatOptions {
  url: string;
  payload: ChatRequest;
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
  fetchImpl?: typeof fetch;
}