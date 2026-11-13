import type { ChatSource } from '@hermes/util-types';

import { parseCitations } from '../citations';
import { CitationChip } from './CitationChip';

export interface MessageTextProps {
  content: string;
  sources: readonly ChatSource[];
  onCitationActivate?: (source: ChatSource) => void;
}

/**
 * Render inline text with basic formatting (bold, inline code)
 * and embedded citation chips.
 */
function renderInlineContent(
  text: string,
  sources: readonly ChatSource[],
  onCitationActivate?: (source: ChatSource) => void,
): React.JSX.Element[] {
  const segments = parseCitations(text, sources);

  return segments.map((segment, segIdx) => {
    if (segment.type === 'citation') {
      return (
        <CitationChip
          key={`chip-${segIdx}-${segment.marker}`}
          segment={segment}
          onActivate={onCitationActivate}
        />
      );
    }

    // Parse inline markdown: **bold** and `code`
    const raw = segment.text;
    const parts = raw.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);

    return (
      <span key={`text-${segIdx}`}>
        {parts.map((part, pIdx) => {
          if (
            part.startsWith('**') &&
            part.endsWith('**') &&
            part.length >= 4
          ) {
            return (
              <strong key={pIdx} className="font-bold text-ivory">
                {part.slice(2, -2)}
              </strong>
            );
          }
          if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
            return (
              <code
                key={pIdx}
                className="border border-border-subtle bg-neutral-950 px-1 py-0.5 text-[11px] text-neon-blue"
              >
                {part.slice(1, -1)}
              </code>
            );
          }
          return part;
        })}
      </span>
    );
  });
}

/** Render assistant text with structured terminal markdown and inline citation chips. */
export function MessageText({
  content,
  sources,
  onCitationActivate,
}: MessageTextProps): React.JSX.Element {
  const lines = content.split('\n');
  const elements: React.JSX.Element[] = [];

  let inCodeBlock = false;
  let codeBuffer: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre
            key={`code-${i}`}
            className="my-2 overflow-x-auto border border-border-subtle bg-neutral-950 p-2 font-mono text-[11px] text-neon-blue"
          >
            <code>{codeBuffer.join('\n')}</code>
          </pre>,
        );
        codeBuffer = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    const headerMatch = line.match(/^(#{1,3})\s+(.*)$/);
    if (headerMatch) {
      elements.push(
        <div
          key={`header-${i}`}
          className="mt-2.5 mb-1 font-bold text-xs uppercase tracking-wider text-ivory"
        >
          {renderInlineContent(headerMatch[2], sources, onCitationActivate)}
        </div>,
      );
      continue;
    }

    const bulletMatch = line.match(/^[-*•]\s+(.*)$/);
    if (bulletMatch) {
      elements.push(
        <div key={`bullet-${i}`} className="my-0.5 flex items-start gap-1.5 pl-1">
          <span className="select-none text-neon-blue">▸</span>
          <span className="flex-1">
            {renderInlineContent(bulletMatch[1], sources, onCitationActivate)}
          </span>
        </div>,
      );
      continue;
    }

    const numMatch = line.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      elements.push(
        <div key={`num-${i}`} className="my-0.5 flex items-start gap-1.5 pl-1">
          <span className="select-none font-bold text-neon-blue tabular-nums">
            {numMatch[1]}.
          </span>
          <span className="flex-1">
            {renderInlineContent(numMatch[2], sources, onCitationActivate)}
          </span>
        </div>,
      );
      continue;
    }

    if (line.trim().length === 0) {
      elements.push(<div key={`empty-${i}`} className="h-2" />);
      continue;
    }

    elements.push(
      <p key={`p-${i}`} className="leading-relaxed">
        {renderInlineContent(line, sources, onCitationActivate)}
      </p>,
    );
  }

  if (inCodeBlock && codeBuffer.length > 0) {
    elements.push(
      <pre
        key="code-unclosed"
        className="my-2 overflow-x-auto border border-border-subtle bg-neutral-950 p-2 font-mono text-[11px] text-neon-blue"
      >
        <code>{codeBuffer.join('\n')}</code>
      </pre>,
    );
  }

  return <div className="space-y-0.5">{elements}</div>;
}
