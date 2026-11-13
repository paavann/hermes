import { useEffect, useState } from 'react';

export function EventsLoader(): React.JSX.Element {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStep((prev) => (prev >= 3 ? 0 : prev + 1));
    }, 300);

    return () => clearInterval(timer);
  }, []);

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed right-3 top-16 z-30 border border-border-subtle bg-black px-2.5 py-1 font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-neon-blue select-none"
    >
      <span>SYNCING</span>
      <span aria-hidden="true" className="ml-1 inline-block text-left">
        <span
          className={`transition-opacity duration-150 ${
            step < 1 ? 'opacity-100' : 'opacity-0'
          }`}
        >
          .
        </span>
        <span
          className={`transition-opacity duration-150 ${
            step < 2 ? 'opacity-100' : 'opacity-0'
          }`}
        >
          .
        </span>
        <span
          className={`transition-opacity duration-150 ${
            step < 3 ? 'opacity-100' : 'opacity-0'
          }`}
        >
          .
        </span>
      </span>
    </div>
  );
}
