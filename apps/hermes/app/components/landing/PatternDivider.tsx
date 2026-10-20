import { useState, useEffect, useRef } from 'react';
import type React from 'react';
import gsap from 'gsap';

import type { PatternLayout, PatternTile } from './types';

export function computePatternLayout(width: number, randomize = true): PatternLayout {
  const isDesktop = width >= 768;

  // 3 rows across 4 columns (desktop) or 3 columns (mobile)
  const colCount = isDesktop ? 4 : 3;
  const rowCount = 3;

  // Subtle width variation across columns while summing strictly to 100% of container width
  const rawWeights = Array.from({ length: colCount }, () =>
    randomize ? 0.98 + Math.random() * 0.04 : 1.0
  );
  const totalWeight = rawWeights.reduce((sum, w) => sum + w, 0);
  const colWidths = rawWeights.map((w) => Math.round((w / totalWeight) * width));

  // Ensure the final column lands flush with the right edge
  const sumExceptLast = colWidths.slice(0, -1).reduce((sum, w) => sum + w, 0);
  colWidths[colWidths.length - 1] = Math.max(width - sumExceptLast, 40);

  // Compute column left positions (starting flush at 0)
  const colLefts: number[] = [];
  let currLeft = 0;
  for (let c = 0; c < colCount; c += 1) {
    colLefts.push(currLeft);
    currLeft += colWidths[c];
  }

  // Row heights proportioned with an increase of 3-4vh total
  const avgColWidth = width / colCount;
  const vh = !randomize || typeof window === 'undefined' ? 900 : window.innerHeight;
  const extraRowHeight = Math.round((vh * 0.035) / rowCount);
  const baseRowHeight = Math.round(avgColWidth * 0.44) + extraRowHeight;
  const rowHeights = [baseRowHeight, baseRowHeight, baseRowHeight];

  const verticalPad = isDesktop ? 24 : 16;
  const rowTops = [
    verticalPad,
    verticalPad + rowHeights[0],
    verticalPad + rowHeights[0] + rowHeights[1],
  ];

  // STRICT CORNER-ONLY RULE:
  // 1. No consecutive boxes in any column: a column can only contain [0], [1], [2], or [0, 2] (never [0, 1] or [1, 2]).
  // 2. No consecutive boxes in any row: adjacent columns can never share the same row index,
  //    and every box must connect via corner (|r - p| === 1) to the adjacent column.
  //    On a 3-row grid, this means columns strictly alternate between [1] and {[0], [2], [0, 2]}.
  const outerChoices: readonly (readonly number[])[] = [[0], [2], [0, 2]];
  const tiles: PatternTile[] = [];

  // Deterministic corner-only pattern for initial SSR render
  const defaultColRows: readonly (readonly number[])[] = [[0, 2], [1], [0], [1]];

  let useMiddleRow = randomize ? Math.random() < 0.5 : false;

  for (let c = 0; c < colCount; c += 1) {
    const chosenRows = !randomize
      ? defaultColRows[c % defaultColRows.length]
      : useMiddleRow
        ? [1]
        : outerChoices[Math.floor(Math.random() * outerChoices.length)];

    useMiddleRow = !useMiddleRow;

    for (const r of chosenRows) {
      tiles.push({
        id: `tile-c${c}-r${r}-${colLefts[c]}-${rowTops[r]}`,
        left: colLefts[c],
        top: rowTops[r],
        width: colWidths[c],
        height: rowHeights[r],
      });
    }
  }

  const containerHeight = verticalPad * 2 + rowHeights[0] + rowHeights[1] + rowHeights[2];

  return {
    containerHeight,
    tiles,
  };
}

export function PatternDivider(): React.JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const tileRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [layout, setLayout] = useState<PatternLayout>(() => computePatternLayout(1440, false));
  const [isInView, setIsInView] = useState<boolean>(false);

  // Keep full width on window resize
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let lastWidth = el.clientWidth || window.innerWidth;
    setLayout(computePatternLayout(lastWidth));

    const handleResize = (): void => {
      const newWidth = el.clientWidth || window.innerWidth;
      if (newWidth > 0 && Math.abs(newWidth - lastWidth) > 2) {
        lastWidth = newWidth;
        setLayout(computePatternLayout(newWidth));
      }
    };

    if (typeof ResizeObserver !== 'undefined') {
      const resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(el);
      return () => resizeObserver.disconnect();
    } else {
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, []);

  // Re-randomize the rectangle layout every time the user scrolls into view
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (typeof window === 'undefined' || typeof window.IntersectionObserver === 'undefined') {
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const width = el.clientWidth || window.innerWidth || 1440;
            setLayout(computePatternLayout(width));
            setIsInView(true);
          } else {
            setIsInView(false);
          }
        });
      },
      { threshold: 0.15 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Animate the rectangles in a random one-by-one order via GSAP (fade in & fade out)
  useEffect(() => {
    const boxes = tileRefs.current
      .slice(0, layout.tiles.length)
      .filter((node): node is HTMLDivElement => node !== null);

    if (boxes.length === 0) return;

    gsap.killTweensOf(boxes);

    if (isInView) {
      const shuffled = [...boxes];
      for (let i = shuffled.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }

      gsap.fromTo(
        shuffled,
        { autoAlpha: 0, scale: 0.94 },
        {
          autoAlpha: 1,
          scale: 1,
          duration: 0.5,
          stagger: 0.08,
          ease: 'power3.out',
          overwrite: 'auto',
        }
      );
    } else {
      const shuffled = [...boxes];
      for (let i = shuffled.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }

      gsap.to(shuffled, {
        autoAlpha: 0,
        scale: 0.94,
        duration: 0.35,
        stagger: 0.04,
        ease: 'power2.in',
        overwrite: 'auto',
      });
    }

    return () => {
      gsap.killTweensOf(boxes);
    };
  }, [layout, isInView]);

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      style={{ height: `${layout.containerHeight}px` }}
      className="w-full overflow-hidden select-none bg-obsidian relative z-40"
    >
      {/* Full-Width Corner-Connected Muted Rectangles (Overlaps across the left margin) */}
      <div className="w-full h-full relative overflow-hidden">
        {layout.tiles.map((tile, idx) => (
          <div
            key={tile.id}
            ref={(node) => {
              tileRefs.current[idx] = node;
            }}
            style={{
              left: `${tile.left}px`,
              top: `${tile.top}px`,
              width: `${tile.width}px`,
              height: `${tile.height}px`,
            }}
            className="absolute bg-white/[0.035] border border-white/[0.04] opacity-0 will-change-transform"
          />
        ))}
      </div>
    </div>
  );
}
