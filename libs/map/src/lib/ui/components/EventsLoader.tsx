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
      className="fixed top-4 right-4 z-10 pointer-events-none select-none bg-[#08929c] text-[#000000] font-mono font-bold text-[10px] tracking-wider px-2 py-0.5 uppercase"
    >
      <span>LOADING</span>
      <span aria-hidden="true" className="inline-block text-left">
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
