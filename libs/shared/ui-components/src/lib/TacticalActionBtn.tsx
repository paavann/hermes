import { useEffect, useRef } from 'react';
import type * as React from 'react';
import gsap from 'gsap';
import { cn } from './utils';

export interface TacticalActionBtnProps {
  readonly label: string;
  readonly loadingLabel?: string;
  readonly isSubmitting?: boolean;
  readonly disabled?: boolean;
  readonly className?: string;
  readonly variant?: 'roll' | 'slide';
  readonly type?: 'submit' | 'button';
  readonly onClick?: () => void;
  readonly ariaLabel?: string;
}

export function TacticalActionBtn({
  label,
  loadingLabel = 'PROCESSING...',
  isSubmitting = false,
  disabled = false,
  className,
  variant = 'roll',
  type = 'submit',
  onClick,
  ariaLabel,
}: TacticalActionBtnProps): React.JSX.Element {
  const text1Ref = useRef<HTMLSpanElement>(null);
  const text2Ref = useRef<HTMLSpanElement>(null);
  const indicatorRef = useRef<HTMLSpanElement>(null);
  const arrow1Ref = useRef<HTMLSpanElement>(null);
  const arrow2Ref = useRef<HTMLSpanElement>(null);
  const scanlineRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const text1El = text1Ref.current;
    const text2El = text2Ref.current;
    const arrow1El = arrow1Ref.current;
    const indicatorEl = indicatorRef.current;
    const arrow2El = arrow2Ref.current;
    const scanlineEl = scanlineRef.current;

    if (variant === 'roll') {
      if (indicatorEl) gsap.set(indicatorEl, { x: -12, opacity: 0, rotation: -90 });
      if (arrow2El) gsap.set(arrow2El, { x: -24, opacity: 0 });
      if (scanlineEl) gsap.set(scanlineEl, { scaleX: 0, transformOrigin: 'left center' });
    } else {
      if (indicatorEl) gsap.set(indicatorEl, { x: -14, opacity: 0 });
      if (arrow2El) gsap.set(arrow2El, { x: -28, opacity: 0 });
    }

    return () => {
      gsap.killTweensOf([
        text1El,
        text2El,
        indicatorEl,
        arrow1El,
        arrow2El,
        scanlineEl,
      ]);
    };
  }, [variant]);

  const handleMouseEnter = (): void => {
    if (isSubmitting || disabled) return;

    if (variant === 'roll') {
      if (
        !text1Ref.current ||
        !text2Ref.current ||
        !indicatorRef.current ||
        !arrow1Ref.current ||
        !arrow2Ref.current ||
        !scanlineRef.current
      ) {
        return;
      }

      gsap.killTweensOf([
        text1Ref.current,
        text2Ref.current,
        indicatorRef.current,
        arrow1Ref.current,
        arrow2Ref.current,
        scanlineRef.current,
      ]);

      gsap.to([text1Ref.current, text2Ref.current], {
        yPercent: -100,
        duration: 0.32,
        ease: 'power3.out',
      });

      gsap.to(indicatorRef.current, {
        x: 0,
        opacity: 1,
        rotation: 0,
        duration: 0.3,
        ease: 'back.out(1.7)',
      });

      gsap.to(arrow1Ref.current, {
        x: 24,
        opacity: 0,
        duration: 0.2,
        ease: 'power2.in',
      });

      gsap.fromTo(
        arrow2Ref.current,
        { x: -24, opacity: 0 },
        { x: 0, opacity: 1, duration: 0.26, delay: 0.06, ease: 'power3.out' }
      );

      gsap.to(scanlineRef.current, {
        scaleX: 1,
        duration: 0.36,
        ease: 'power3.out',
      });
    } else {
      if (
        !text1Ref.current ||
        !indicatorRef.current ||
        !arrow1Ref.current ||
        !arrow2Ref.current
      ) {
        return;
      }

      gsap.killTweensOf([
        text1Ref.current,
        indicatorRef.current,
        arrow1Ref.current,
        arrow2Ref.current,
      ]);

      gsap.to(text1Ref.current, {
        x: 10,
        duration: 0.28,
        ease: 'power3.out',
      });

      gsap.to(indicatorRef.current, {
        x: 0,
        opacity: 1,
        duration: 0.28,
        ease: 'power3.out',
      });

      gsap.to(arrow1Ref.current, {
        x: 28,
        opacity: 0,
        duration: 0.22,
        ease: 'power2.in',
      });

      gsap.fromTo(
        arrow2Ref.current,
        { x: -28, opacity: 0 },
        { x: 0, opacity: 1, duration: 0.26, delay: 0.08, ease: 'power3.out' }
      );
    }
  };

  const handleMouseLeave = (): void => {
    if (isSubmitting || disabled) return;

    if (variant === 'roll') {
      if (
        !text1Ref.current ||
        !text2Ref.current ||
        !indicatorRef.current ||
        !arrow1Ref.current ||
        !arrow2Ref.current ||
        !scanlineRef.current
      ) {
        return;
      }

      gsap.killTweensOf([
        text1Ref.current,
        text2Ref.current,
        indicatorRef.current,
        arrow1Ref.current,
        arrow2Ref.current,
        scanlineRef.current,
      ]);

      gsap.to([text1Ref.current, text2Ref.current], {
        yPercent: 0,
        duration: 0.26,
        ease: 'power2.inOut',
      });

      gsap.to(indicatorRef.current, {
        x: -12,
        opacity: 0,
        rotation: -90,
        duration: 0.22,
        ease: 'power2.inOut',
      });

      gsap.to(arrow1Ref.current, {
        x: 0,
        opacity: 1,
        duration: 0.24,
        ease: 'power2.inOut',
      });

      gsap.to(arrow2Ref.current, {
        x: -24,
        opacity: 0,
        duration: 0.2,
        ease: 'power2.inOut',
      });

      gsap.to(scanlineRef.current, {
        scaleX: 0,
        duration: 0.26,
        ease: 'power2.inOut',
      });
    } else {
      if (
        !text1Ref.current ||
        !indicatorRef.current ||
        !arrow1Ref.current ||
        !arrow2Ref.current
      ) {
        return;
      }

      gsap.killTweensOf([
        text1Ref.current,
        indicatorRef.current,
        arrow1Ref.current,
        arrow2Ref.current,
      ]);

      gsap.to(text1Ref.current, {
        x: 0,
        duration: 0.24,
        ease: 'power2.inOut',
      });

      gsap.to(indicatorRef.current, {
        x: -14,
        opacity: 0,
        duration: 0.24,
        ease: 'power2.inOut',
      });

      gsap.to(arrow1Ref.current, {
        x: 0,
        opacity: 1,
        duration: 0.24,
        ease: 'power2.inOut',
      });

      gsap.to(arrow2Ref.current, {
        x: -28,
        opacity: 0,
        duration: 0.2,
        ease: 'power2.inOut',
      });
    }
  };

  const activeText = isSubmitting ? loadingLabel : label;

  return (
    <button
      type={type}
      disabled={disabled || isSubmitting}
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={cn(
        'group relative w-full bg-ivory text-black hover:bg-neon-blue hover:text-black transition-colors duration-200 text-xs uppercase tracking-widest font-bold font-mono flex items-center justify-between cursor-pointer rounded-none disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden',
        variant === 'roll' ? 'py-3.5 px-6' : 'py-4 px-6',
        isSubmitting && 'bg-neon-blue text-black',
        className
      )}
      aria-label={ariaLabel || activeText}
    >
      {variant === 'roll' ? (
        <>
          {/* Left tactical square indicator */}
          <div className="relative flex items-center w-6">
            <span
              ref={indicatorRef}
              className="text-[9px] text-black select-none pointer-events-none opacity-0"
              aria-hidden="true"
            >
              ■
            </span>
          </div>

          {/* Center rolling label */}
          <div className="relative h-4 overflow-hidden flex flex-col items-center justify-start select-none">
            <span ref={text1Ref} className="block leading-4 tracking-widest">
              {activeText}
            </span>
            <span
              ref={text2Ref}
              className="block leading-4 tracking-widest font-extrabold text-black"
            >
              {activeText}
            </span>
          </div>

          {/* Right projectile arrow */}
          <div className="relative w-6 h-4 overflow-hidden flex items-center justify-end select-none pointer-events-none">
            <span ref={arrow1Ref} className="block text-sm leading-none">
              →
            </span>
            <span
              ref={arrow2Ref}
              className="absolute right-0 block text-sm leading-none opacity-0"
              aria-hidden="true"
            >
              →
            </span>
          </div>

          {/* Subtle bottom tactical sweep bar */}
          <span
            ref={scanlineRef}
            className="absolute bottom-0 left-0 right-0 h-[2px] bg-black/40 pointer-events-none"
            aria-hidden="true"
          />
        </>
      ) : (
        <>
          {/* Left side: text with slide indicator */}
          <div className="relative flex items-center">
            <span
              ref={indicatorRef}
              className="absolute -left-1 text-black font-black select-none pointer-events-none opacity-0 text-[10px]"
              aria-hidden="true"
            >
              ■
            </span>
            <span ref={text1Ref} className="block tracking-widest select-none">
              {activeText}
            </span>
          </div>

          {/* Right side: projectile arrow cycle */}
          <div className="relative w-8 h-4 overflow-hidden flex items-center justify-end select-none pointer-events-none">
            <span ref={arrow1Ref} className="block text-base leading-none">
              →
            </span>
            <span
              ref={arrow2Ref}
              className="absolute right-0 block text-base leading-none opacity-0"
              aria-hidden="true"
            >
              →
            </span>
          </div>
        </>
      )}
    </button>
  );
}
