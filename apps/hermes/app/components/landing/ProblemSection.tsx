import { useState, useEffect, useRef } from 'react'
import type React from 'react'
import { cn } from '@hermes/ui-components'
import { PatternDivider } from './PatternDivider'
import type { ProblemStatement } from './types'



export const PROBLEM_STATEMENTS: readonly ProblemStatement[] = [
  {
    id: 'statement-1',
    text: 'The world moves in physical coordinates, yet our understanding of it remains trapped in linear text feeds designed for engagement rather than truth.',
  },
  {
    id: 'statement-2',
    text: 'Headlines tell you that something happened. They fail to show where it happened, how close it is to what matters, or what chain of events led there.',
  },
  {
    id: 'statement-3',
    text: 'Consuming hundreds of fragmented alerts creates noise and cognitive fatigue, not intelligence.',
  },
  {
    id: 'statement-4',
    text: 'To understand critical global shifts, we must observe them spatially—connecting geographic proximity, consensus, and causal history in a single unified view.',
  },
] as const





export function ProblemSection(): React.JSX.Element {
  const [activeIdx, setActiveIdx] = useState<number>(0)
  const itemRefs = useRef<(HTMLDivElement | null)[]>([])



  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.IntersectionObserver === 'undefined') {
      return
    }

    const observers: IntersectionObserver[] = []

    itemRefs.current.forEach((el, index) => {
      if (!el) return

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setActiveIdx(index)
            }
          });
        },
        {
          rootMargin: '-20% 0px -20% 0px',
          threshold: 0.35,
        }
      )

      observer.observe(el)
      observers.push(observer)
    })

    return () => {
      observers.forEach((obs) => obs.disconnect());
    }
  }, [])

  return (
    <section id="problem" className="relative w-full flex flex-col scroll-mt-16">
      <div className="flex flex-col md:flex-row w-full">
        <div className="w-45 md:w-55 shrink-0 p-5 md:p-8 hidden md:block">
          <div className="sticky top-24">
            <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2">
              <span className="text-neon-blue">■</span>
              <span>The Problem</span>
            </h2>
            <div className="mt-4 text-[10px] text-slate-muted/50 tracking-widest font-mono">
              01 // THE PARADOX
            </div>
          </div>
        </div>

        <div className="flex-1 p-5 md:pl-10 md:pr-12 pt-5 md:pt-8 pb-16 md:pb-28 max-w-5xl">
          <div className="md:hidden mb-8">
            <h2 className="text-xs uppercase tracking-widest text-ivory flex items-center gap-2">
              <span className="text-neon-blue">■</span>
              <span>The Problem</span>
            </h2>
          </div>

          <div className="space-y-20 md:space-y-28 ml-10 mt-10">
            {PROBLEM_STATEMENTS.map((item, index) => {
              const isActive = activeIdx === index;
              const isAdjacent = Math.abs(activeIdx - index) === 1;

              return (
                <div
                  key={item.id}
                  ref={(el) => { itemRefs.current[index] = el }}
                  className={cn(
                    'transition-all duration-500 ease-out select-none cursor-default',
                    isActive
                      ? 'text-ivory font-medium opacity-100 translate-x-1'
                      : isAdjacent
                        ? 'text-slate-muted/70 opacity-60'
                        : 'text-slate-muted/30 opacity-30'
                  )}
                >
                  <p className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl leading-snug md:leading-[1.3] tracking-tight">
                    {item.text}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <PatternDivider />
    </section>
  );
}
