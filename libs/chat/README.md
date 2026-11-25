# @hermes/chat

Conversational RAG client for Project Hermes. It holds the conversation in a
module-level Zustand store persisted to `localStorage`, parses the API's
Server-Sent Events stream, resolves the map scope for each turn, renders inline
citations, and exposes the HUD chat panel.

The library never talks to a model provider directly; it posts to
`POST /api/{apiVer}/chat` and consumes the stream. Server-side conversation
memory is owned by the API: the current deployment checkpoints turns in process
memory, so a server restart starts a fresh memory thread even though the client
keeps its transcript.

## Composition

`ChatPanel` owns the `useChat` hook and renders its own closed-state rail. Mount
it inside a positioned map container and provide the API configuration through
`ChatConfigProvider`.

```tsx
import { ChatConfigProvider, ChatPanel } from '@hermes/chat';
import type { AutoScope } from '@hermes/chat';
import type { BoundingBox, ChatSource } from '@hermes/util-types';

interface MapChatProps {
  selectedEventId: string | null;
  viewport: BoundingBox | null;
  onCitedEventsChange: (sources: ChatSource[]) => void;
  onCitationActivate: (source: ChatSource) => void;
}

export function MapChat({
  selectedEventId,
  viewport,
  onCitedEventsChange,
  onCitationActivate,
}: MapChatProps) {
  const autoScope: AutoScope = {
    eventId: selectedEventId,
    viewport,
  };

  return (
    <ChatConfigProvider
      config={{ baseUrl: import.meta.env.VITE_BASE_URL, apiVer: 'v1' }}
    >
      <ChatPanel
        autoScope={autoScope}
        onSources={onCitedEventsChange}
        onCitationActivate={onCitationActivate}
      />
    </ChatConfigProvider>
  );
}
```

The panel is an overlay, not a route. Closing it aborts an active stream, marks
the partial answer `cancelled`, clears citation highlights through `onSources`,
and preserves the conversation store for the next open. Citation-driven map
focus is owned by the app: `onCitationActivate` receives event, article, and
timeline sources that have plotted coordinates; web sources are opened in a new
tab by `useChat` and never move the map.

## Scope contract

`useChat` attaches `context: { event_id, bbox }` from the live map state to every request and lets the backend infer `event`, `viewport`, or `global` scope during query planning (`global` for vague summaries, `viewport` for screen-view queries, and `event` for selected-event follow-ups).

## Store

`useChatStore` is a module-level Zustand store persisted to `localStorage`
under the `hermes-chat` key:

- `messages`: `{ id, role, content, status, stage, sources, done, error }[]`
- `threadId`: server-side conversation key, sent as `thread_id`
- `updatedAt`: epoch millisecond timestamp used to expire idle conversations after 12 hours (`CHAT_PERSIST_TTL_MS`)
- `isOpen`, `isStreaming`, `activeId`
- `send`, `retry`, `cancel`, `clear`, `setOpen`, `toggleOpen`, `applyEvent`, `fail`

Only `threadId`, `updatedAt`, and `messages` are persisted. Stale `streaming` messages
rehydrate as `cancelled`, and threads older than `CHAT_PERSIST_TTL_MS` expire cleanly into a fresh `threadId`. `clear` empties the conversation and generates a new
`threadId`, so the server starts a fresh memory thread.

`stage` mirrors the latest `status` event (`accepted`, `planning`, `retrieving`,
`searching`, `generating`, `finalizing`). The bubble shows it as a waiting label
until the first token arrives; `done`, `error`, and `cancelled` clear it.

## Transport

`streamChat` posts JSON with native `fetch` and parses the response body with
`TextDecoder`. `parseSseStream` handles CRLF, comments, multi-line `data:`
fields, arbitrary chunk boundaries, unknown event types, and a trailing frame
without a blank line.

Non-2xx responses are parsed as the API error envelope (`err_code`, `err_msg`,
`details`). `ChatTransportError` exposes `status`, `code`, `retryAfter`, and
`retryable`; `chatErrorFromTransport` maps unknown codes to `INTERNAL_ERROR`.
A stream that ends without `done` or `error` is rejected as incomplete.

## Citations

`parseCitations(text, sources)` maps `[E#]`, `[A#]`, `[T#]`, and `[W#]` markers
to the `sources` event records in first-citation order, and treats `[BG]` as
background knowledge. The first distinct marker of each kind maps to the first
source of that kind, and repeated markers resolve to the same source.
`resolveCitationSources(content, sources)` builds the message-wide marker map so
per-line rendering of a long answer keeps marker numbers aligned.

## Testing

```bash
npx nx test @hermes/chat
```

The suite covers the store, SSE parser, hook scope resolution, citation
rendering, and the panel's open/close, streaming, retry, and keyboard behavior
with a mocked transport. No test reaches the network or a model provider.
