import { useEffect, useState, useRef } from 'react';
import gsap from 'gsap';

interface BootSequenceProps {
  onComplete: () => void;
}

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>[]{}';

export function BootSequence({ onComplete }: BootSequenceProps) {
  const [text, setText] = useState('');
  const [showCursor, setShowCursor] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    // Blinking cursor effect
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 400);

    const targetText = 'HERMES';
    let iterations = 0;
    const maxIterations = 20;

    // Start scramble after 1 second of just blinking cursor
    const startDelay = setTimeout(() => {
      const scrambleInterval = setInterval(() => {
        setText((prev) => {
          let newText = '';
          for (let i = 0; i < targetText.length; i++) {
            if (i < iterations / 3) {
              newText += targetText[i];
            } else {
              newText += CHARS[Math.floor(Math.random() * CHARS.length)];
            }
          }
          return newText;
        });

        iterations += 1;
        if (iterations >= maxIterations * 3) {
          clearInterval(scrambleInterval);
          setText(targetText);
          
          // Hold for 1 second, then snap away instantly (0s duration as requested)
          setTimeout(() => {
            if (containerRef.current) {
              gsap.to(containerRef.current, {
                duration: 0, 
                display: 'none',
                onComplete: onComplete
              });
            } else {
                onComplete();
            }
          }, 1000);
        }
      }, 40); // speed of scramble
      
      return () => clearInterval(scrambleInterval);
    }, 1000);

    return () => {
      clearInterval(cursorInterval);
      clearTimeout(startDelay);
    };
  }, [onComplete]);

  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#050505]"
    >
      <div className="font-mono text-neon-blue text-5xl md:text-7xl tracking-[0.2em] font-bold">
        {text}
        <span className={`${showCursor ? 'opacity-100' : 'opacity-0'}`}>_</span>
      </div>
    </div>
  );
}
