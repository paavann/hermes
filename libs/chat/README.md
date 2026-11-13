# @hermes/chat

Stateless conversational RAG client for Project Hermes. It holds the in-memory
conversation, parses the API's Server-Sent Events stream, resolves the map
scope for each turn, renders inline citations, and exposes the HUD chat panel.

The library never persists messages and never talks to a model provider
directly; it posts to `POST /api/{apiVer}/chat` and consumes the stream.

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
the partial answer `cancelled`, and preserves the conversation store for the
next open. Citation-driven map focus is owned by the app: `onCitationActivate`
receives event, article, and timeline sources that have plotted coordinates;
web sources are opened in a new tab by `useChat` and never move the map.

## Scope contract

The request scope is resolved from the session mode and the current map state:

| Mode       | Resolution                                                     |
| :--------- | :------------------------------------------------------------- |
| `auto`     | selected event, else viewport, else global                     |
| `event`    | selected event, else viewport, else global                     |
| `viewport` | current viewport, else global                                  |
| `global`   | global plottings                                               |

An explicit mode is stored in the Zustand store and persists for the session.
The underlying event ID and bounding box keep following the map, so an explicit
`event` or `viewport` choice never freezes a stale value.

## Store

`useChatStore` is a module-level Zustand store:

- `messages`: `{ id, role, content, status, sources, done, error }[]`
- `isOpen`, `isStreaming`, `activeId`, `scopeOverride`
- `send`, `retry`, `cancel`, `clear`, `setOpen`, `toggleOpen`,
  `setScopeOverride`, `applyEvent`, `fail`

`buildHistory` sends at most the last 16 completed messages (eight turns),
strips `[E#]`, `[A#]`, `[T#]`, `[W#]`, and `[BG]` markers, and caps each
message at 8,000 characters.

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
background knowledge. `CitationChip` renders focusable sources as buttons,
marks web evidence as external, and leaves unresolved or coordinate-less
sources inert.

## Testing

```bash
npx nx test @hermes/chat
```

The suite covers the store, SSE parser, hook scope resolution, citation
rendering, and the panel's open/close, streaming, retry, and keyboard behavior
with a mocked transport. No test reaches the network or a model provider.
