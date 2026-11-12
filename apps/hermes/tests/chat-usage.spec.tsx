import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// eslint-disable-next-line @nx/enforce-module-boundaries -- this test exercises the documented public API directly
import { ChatConfigProvider, ChatPanel, useChatStore } from '@hermes/chat';
import type { AutoScope } from '@hermes/chat';
import type { BoundingBox, ChatSource } from '@hermes/util-types';

interface MapChatProps {
  selectedEventId: string | null;
  viewport: BoundingBox | null;
  onCitedEventsChange: (sources: ChatSource[]) => void;
  onCitationActivate: (source: ChatSource) => void;
}

/** Mirrors the composition example in libs/chat/README.md. */
function MapChat({
  selectedEventId,
  viewport,
  onCitedEventsChange,
  onCitationActivate,
}: MapChatProps): React.JSX.Element {
  const autoScope: AutoScope = {
    eventId: selectedEventId,
    viewport,
  };

  return (
    <ChatConfigProvider config={{ baseUrl: 'http://localhost:8000', apiVer: 'v1' }}>
      <ChatPanel
        autoScope={autoScope}
        onSources={onCitedEventsChange}
        onCitationActivate={onCitationActivate}
      />
    </ChatConfigProvider>
  );
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

describe('README composition example', () => {
  it('mounts the panel inside a positioned map container', () => {
    render(
      <div className="relative h-screen">
        <MapChat
          selectedEventId={null}
          viewport={{ north: 60, south: 30, east: 60, west: 20 }}
          onCitedEventsChange={vi.fn()}
          onCitationActivate={vi.fn()}
        />
      </div>,
    );

    expect(screen.getByRole('button', { name: 'Open chat' })).toBeTruthy();
  });
});
