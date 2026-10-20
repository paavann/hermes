import { useRef } from 'react';
import type * as React from 'react';
import { Link } from 'react-router';
import gsap from 'gsap';
import { cn } from './utils';

export interface RollButtonProps {
  readonly to?: string;
  readonly href?: string;
  readonly label?: string;
  readonly hoverLabel?: string;
  readonly className?: string;
  readonly ariaLabel?: string;
  readonly onClick?: () => void;
  readonly id?: string;
}

export function RollButton({
  to,
  href,
  label = 'LAUNCH MAP',
  hoverLabel = 'LAUNCH MAP ↗',
  className,
  ariaLabel = 'Launch the intelligence map',
  onClick,
  id,
}: RollButtonProps): React.JSX.Element {
  const text1Ref = useRef<HTMLSpanElement>(null);
  const text2Ref = useRef<HTMLSpanElement>(null);

  const handleMouseEnter = (): void => {
    if (!text1Ref.current || !text2Ref.current) return;
    gsap.killTweensOf([text1Ref.current, text2Ref.current]);
    gsap.to([text1Ref.current, text2Ref.current], {
      yPercent: -100,
      duration: 0.32,
      ease: 'power3.out',
    });
  };

  const handleMouseLeave = (): void => {
    if (!text1Ref.current || !text2Ref.current) return;
    gsap.killTweensOf([text1Ref.current, text2Ref.current]);
    gsap.to([text1Ref.current, text2Ref.current], {
      yPercent: 0,
      duration: 0.28,
      ease: 'power2.inOut',
    });
  };

  const content = (
    <div className="relative h-4 overflow-hidden flex flex-col items-center justify-start select-none">
      <span ref={text1Ref} className="block leading-4">
        {label}
      </span>
      <span ref={text2Ref} className="block leading-4 text-black font-extrabold">
        {hoverLabel}
      </span>
    </div>
  );

  const combinedClassName = cn(
    'group relative inline-flex items-center justify-center overflow-hidden bg-ivory text-obsidian px-4 py-1.5 font-mono text-xs font-bold uppercase tracking-wider transition-colors duration-200 hover:bg-white cursor-pointer select-none',
    className
  );

  if (to) {
    return (
      <Link
        to={to}
        id={id}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={onClick}
        className={combinedClassName}
        aria-label={ariaLabel}
      >
        {content}
      </Link>
    );
  }

  if (href) {
    return (
      <a
        href={href}
        id={id}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={onClick}
        className={combinedClassName}
        aria-label={ariaLabel}
      >
        {content}
      </a>
    );
  }

  return (
    <button
      type="button"
      id={id}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      className={combinedClassName}
      aria-label={ariaLabel}
    >
      {content}
    </button>
  );
}
