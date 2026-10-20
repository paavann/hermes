import { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import type { CheckerboardLayout, SquareCell } from './types';

function computeCheckerboardLayout(width: number, height: number): CheckerboardLayout {
  const safeWidth = Math.max(width, 240);
  const safeHeight = Math.max(height, 600);

  // 5-6 columns across the pattern space (5 on narrower panels, 6 on standard/wide desktop)
  const colCount = safeWidth >= 380 ? 4 : 3;

  // Distribute integer pixel widths evenly so adjacent corners meet with zero gaps
  const colLefts: number[] = [];
  const colWidths: number[] = [];
  for (let c = 0; c < colCount; c += 1) {
    const left = Math.round((c * safeWidth) / colCount);
    const right = Math.round(((c + 1) * safeWidth) / colCount);
    colLefts.push(left);
    colWidths.push(right - left);
  }

  // 1:1 true square height matching column width, automatically scaling row count to fill height
  const squareSize = Math.max(Math.round(safeWidth / colCount), 24);
  const rowCount = Math.ceil(safeHeight / squareSize) + 1;

  const cells: SquareCell[] = [];

  for (let r = 0; r < rowCount; r += 1) {
    for (let c = 0; c < colCount; c += 1) {
      // Strictly alternating checkerboard so squares only ever touch at their corners
      if ((r + c) % 2 === 0) {
        cells.push({
          id: `sq-r${r}-c${c}`,
          left: colLefts[c],
          top: r * squareSize,
          width: colWidths[c],
          height: squareSize,
        });
      }
    }
  }

  return { cells };
}

export function AuthCheckerboardPattern(): React.JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const tileRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [layout, setLayout] = useState<CheckerboardLayout>(() =>
    computeCheckerboardLayout(440, 960)
  );
  const [isInView, setIsInView] = useState<boolean>(false);

  // Measure panel dimensions so squares always fill 100% of the right-side space
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let lastWidth = el.clientWidth || Math.round(window.innerWidth * 0.3);
    let lastHeight = el.clientHeight || window.innerHeight;
    setLayout(computeCheckerboardLayout(lastWidth, lastHeight));

    const handleResize = (): void => {
      const newWidth = el.clientWidth || Math.round(window.innerWidth * 0.3);
      const newHeight = el.clientHeight || window.innerHeight;
      if (
        newWidth > 0 &&
        newHeight > 0 &&
        (Math.abs(newWidth - lastWidth) > 2 || Math.abs(newHeight - lastHeight) > 2)
      ) {
        lastWidth = newWidth;
        lastHeight = newHeight;
        setLayout(computeCheckerboardLayout(newWidth, newHeight));
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

  // Trigger animation when in view
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
          setIsInView(entry.isIntersecting);
        });
      },
      { threshold: 0.1 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Random one-by-one GSAP reveal (placement stays fixed, only reveal order is randomized)
  useEffect(() => {
    const boxes = tileRefs.current
      .slice(0, layout.cells.length)
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
          duration: 0.45,
          stagger: 0.025,
          ease: 'power3.out',
          overwrite: 'auto',
        }
      );
    } else {
      gsap.set(boxes, { autoAlpha: 0, scale: 0.94 });
    }

    return () => {
      gsap.killTweensOf(boxes);
    };
  }, [layout, isInView]);

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className="w-full h-full relative overflow-hidden select-none pointer-events-none"
    >
      {layout.cells.map((cell, idx) => (
        <div
          key={cell.id}
          ref={(node) => {
            tileRefs.current[idx] = node;
          }}
          style={{
            left: `${cell.left}px`,
            top: `${cell.top}px`,
            width: `${cell.width}px`,
            height: `${cell.height}px`,
          }}
          className="absolute bg-white/[0.035] border border-white/[0.04] opacity-0 will-change-transform"
        />
      ))}
    </div>
  );
}
