import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { ChatSource } from '@hermes/util-types';

import {
  isFocusableSource,
  parseCitations,
  renderCitations,
} from './citations';

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

const articleSource: ChatSource = {
  kind: 'article',
  id: 'article-uuid',
  event_id: 'event-uuid',
  title: 'Talks resume',
  url: 'https://example.com/talks',
  source_name: 'Example News',
  published_at: '2026-11-07T10:00:00Z',
  retrieved_at: null,
  latitude: 46.2044,
  longitude: 6.1432,
  is_external: false,
  snippet: null,
};

const timelineSource: ChatSource = {
  kind: 'timeline',
  id: 'event-uuid:node-uuid',
  event_id: 'event-uuid',
  title: '2024 ceasefire',
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
  id: 'https://news.example.com/update',
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

describe('parseCitations', () => {
  it('maps markers of each kind to sources in citation order', () => {
    const segments = parseCitations(
      'Alpha [E2] beta [A1] gamma [T1] delta [W1].',
      [eventSource, articleSource, timelineSource, webSource],
    );

    expect(segments).toEqual([
      { type: 'text', text: 'Alpha ' },
      {
        type: 'citation',
        marker: 'E2',
        kind: 'event',
        source: eventSource,
        focusable: true,
      },
      { type: 'text', text: ' beta ' },
      {
        type: 'citation',
        marker: 'A1',
        kind: 'article',
        source: articleSource,
        focusable: true,
      },
      { type: 'text', text: ' gamma ' },
      {
        type: 'citation',
        marker: 'T1',
        kind: 'timeline',
        source: timelineSource,
        focusable: true,
      },
      { type: 'text', text: ' delta ' },
      {
        type: 'citation',
        marker: 'W1',
        kind: 'web',
        source: webSource,
        focusable: true,
      },
      { type: 'text', text: '.' },
    ]);
  });

  it('splits grouped markers and treats background specially', () => {
    const segments = parseCitations('[E1, A1, BG]', [
      eventSource,
      articleSource,
    ]);

    expect(segments.map((segment) => segment.type)).toEqual([
      'citation',
      'citation',
      'citation',
    ]);
    expect(segments[0]).toMatchObject({ marker: 'E1', source: eventSource });
    expect(segments[1]).toMatchObject({ marker: 'A1', source: articleSource });
    expect(segments[2]).toMatchObject({
      marker: 'BG',
      kind: 'background',
      source: null,
      focusable: false,
    });
  });

  it('keeps unknown and incomplete markers as text', () => {
    expect(parseCitations('Fact [X9] and [E1', [eventSource])).toEqual([
      { type: 'text', text: 'Fact [X9] and [E1' },
    ]);
  });

  it('does not invent sources when more markers than sources exist', () => {
    const segments = parseCitations('[E1] [E2]', [eventSource]);

    expect(segments[0]).toMatchObject({ source: eventSource, focusable: true });
    expect(segments[2]).toMatchObject({ source: null, focusable: false });
  });

  it('treats sources without coordinates or URLs as non-focusable', () => {
    const unplotted: ChatSource = {
      ...eventSource,
      latitude: null,
      longitude: null,
    };
    const noUrl: ChatSource = { ...webSource, url: null };

    expect(isFocusableSource(unplotted)).toBe(false);
    expect(isFocusableSource(noUrl)).toBe(false);
    expect(isFocusableSource(eventSource)).toBe(true);
    expect(isFocusableSource(webSource)).toBe(true);
  });
});

describe('renderCitations', () => {
  it('renders clickable citation buttons and forwards the source', () => {
    const onActivate = vi.fn();
    render(
      <p>{renderCitations('Answer [E1].', [eventSource], { onActivate })}</p>,
    );

    const button = screen.getByRole('button', {
      name: 'Open source: Ceasefire talks resume in Geneva',
    });
    expect(button.textContent).toBe('[E1]');
    expect(button.getAttribute('data-citation')).toBe('E1');

    fireEvent.click(button);
    expect(onActivate).toHaveBeenCalledWith(eventSource);
  });

  it('styles background knowledge as unverified and inert', () => {
    const { container } = render(<p>{renderCitations('Context [BG].', [])}</p>);

    const background = container.querySelector('[data-citation="BG"]');
    expect(background).not.toBeNull();
    expect(background?.tagName).toBe('SPAN');
    expect(background?.className).toContain('bg-warning-yellow');
    expect(background?.className).toContain('text-black');
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('renders unresolved markers as plain text', () => {
    render(<p>{renderCitations('Unknown [E4].', [])}</p>);

    const marker = screen.getByText('[E4]');
    expect(marker.tagName).toBe('SPAN');
    expect(marker.className).toContain('cursor-default');
  });

  it('styles web citations as external evidence', () => {
    render(<p>{renderCitations('Update [W1].', [webSource])}</p>);

    const button = screen.getByRole('button', {
      name: 'Open source: Regional update',
    });
    expect(button.className).toContain('text-warning-yellow');
  });
});
