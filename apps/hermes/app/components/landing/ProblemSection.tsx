import { useEffect, useRef, useState } from 'react';
import type React from 'react';

import { cn } from '@hermes/ui-components';

import { PatternDivider } from './PatternDivider';
import { SectionHeading, SectionRail } from './SectionChrome';
import type { ProblemStatement } from './types';

export const PROBLEM_STATEMENTS: readonly ProblemStatement[] = [
  {
    id: 'statement-1',
    index: '01',
    label: 'THE PARADOX',
    text: 'The world moves in physical coordinates, yet our understanding of it remains trapped in linear text feeds designed for engagement rather than truth.',
  },
  {
    id: 'statement-2',
    index: '02',
    label: 'THE GAP',
    text: 'Headlines tell you that something happened. They fail to show where it happened, how close it is to what matters, or what chain of events led there.',
  },
  {
    id: 'statement-3',
    index: '03',
    label: 'THE NOISE',
    text: 'Consuming hundreds of fragmented alerts creates noise and cognitive fatigue, not intelligence.',
  },
  {
    id: 'statement-4',
    index: '04',
    label: 'THE FRAME',
    text: 'To understand critical global shifts, we must observe them spatially — connecting geographic proximity, consensus, and causal history in a single unified view.',
  },
] as const;

export function ProblemSection(): React.JSX.Element {
  const [activeIdx, setActiveIdx] = useState<number>(0);
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (
      typeof window === 'undefined' ||
      typeof window.IntersectionObserver === 'undefined'
    ) {
      return;
    }

    const observers: IntersectionObserver[] = [];

    itemRefs.current.forEach((el, index) => {
      if (!el) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setActiveIdx(index);
            }
          });
        },
        {
          rootMargin: '-20% 0px -20% 0px',
          threshold: 0.35,
        },
      );

      observer.observe(el);
      observers.push(observer);
    });

    return () => {
      observers.forEach((obs) => obs.disconnect());
    };
  }, []);

  const jumpToStatement = (index: number): void => {
    setActiveIdx(index);
    itemRefs.current[index]?.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    });
  };

  return (
    <section
      id="problem"
      className="relative flex w-full flex-col border-t border-border-subtle scroll-mt-16"
    >
      <div className="mx-auto flex w-full max-w-[1600px] flex-col md:flex-row">
        <SectionRail index="02" label="The Problem" meta="Why spatial context matters">
          <nav aria-label="Problem statements" className="mt-10 space-y-1">
            {PROBLEM_STATEMENTS.map((statement, idx) => {
              const isActive = activeIdx === idx;
              return (
                <button
                  key={statement.id}
                  type="button"
                  onClick={() => jumpToStatement(idx)}
                  aria-current={isActive ? 'true' : undefined}
                  className={cn(
                    'group flex w-full cursor-pointer items-center gap-3 border-l py-2.5 pl-3 text-left transition-colors duration-150 focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2',
                    isActive
                      ? 'border-neon-blue bg-white/[0.025] text-ivory'
                      : 'border-border-subtle/50 text-slate-muted/55 hover:border-border-bright hover:text-bone',
                  )}
                >
                  <span
                    className={cn(
                      'tabular-nums text-[9px] transition-colors',
                      isActive ? 'text-neon-blue' : 'text-slate-muted/35',
                    )}
                  >
                    {statement.index}
                  </span>
                  <span className="text-[9px] uppercase tracking-[0.18em]">
                    {statement.label}
                  </span>
                </button>
              );
            })}
          </nav>

          <div className="mt-10 border-t border-border-subtle pt-4">
            <p className="text-[9px] uppercase leading-relaxed tracking-[0.16em] text-slate-muted/40">
              Scroll to advance
              <span className="ml-1 text-neon-blue">↓</span>
            </p>
          </div>
        </SectionRail>

        <div className="min-w-0 flex-1 border-border-subtle/60 px-5 py-12 md:border-l md:py-16 md:pl-10 md:pr-12 lg:pl-14 lg:pr-16">
          <SectionHeading
            index="02"
            label="The Problem"
            meta="04 statements / The paradox"
            className="md:hidden"
          />

          <div className="mt-10 space-y-14 md:mt-4 md:space-y-20 lg:space-y-24">
            {PROBLEM_STATEMENTS.map((item, index) => {
              const isActive = activeIdx === index;
              const isAdjacent = Math.abs(activeIdx - index) === 1;

              return (
                <div
                  key={item.id}
                  ref={(el) => {
                    itemRefs.current[index] = el;
                  }}
                  className={cn(
                    'scroll-mt-32 border-l pl-5 transition-all duration-300 ease-out select-none md:pl-7',
                    isActive
                      ? 'border-neon-blue opacity-100'
                      : isAdjacent
                        ? 'border-border-subtle/60 opacity-60'
                        : 'border-border-subtle/30 opacity-40',
                  )}
                >
                  <div className="mb-3 flex items-center gap-3 text-[9px] uppercase tracking-[0.2em]">
                    <span
                      className={cn(
                        'tabular-nums',
                        isActive ? 'text-neon-blue' : 'text-slate-muted/45',
                      )}
                    >
                      {item.index}
                    </span>
                    <span
                      className={
                        isActive ? 'text-bone/70' : 'text-slate-muted/35'
                      }
                    >
                      {item.label}
                    </span>
                    <span
                      className="h-px flex-1 bg-border-subtle/40"
                      aria-hidden="true"
                    />
                  </div>
                  <p
                    className={cn(
                      'max-w-4xl font-display text-[1.65rem] leading-[1.14] tracking-[-0.02em] sm:text-3xl md:text-[2.4rem] lg:text-[2.85rem]',
                      isActive ? 'text-ivory' : 'text-bone/90',
                    )}
                  >
                    {item.text}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="mt-16 flex items-center justify-between border-t border-border-subtle pt-5 md:mt-20">
            <span className="text-[9px] uppercase tracking-[0.2em] text-slate-muted/40">
              From noise to spatial understanding
            </span>
            <a
              href="#capabilities"
              className="group inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-bone/70 transition-colors hover:text-neon-blue focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-4"
            >
              <span>PROCEED TO CAPABILITIES</span>
              <span
                aria-hidden="true"
                className="transition-transform duration-150 group-hover:translate-x-1"
              >
                →
              </span>
            </a>
          </div>
        </div>
      </div>

      <PatternDivider />
    </section>
  );
}
