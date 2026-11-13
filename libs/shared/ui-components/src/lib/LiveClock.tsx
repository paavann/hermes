import { useState, useEffect } from 'react';

import { cn } from './utils';

export interface LiveClockProps {
  className?: string;
}

export function LiveClock({ className }: LiveClockProps): React.JSX.Element {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      // Format: HH:MM:SS from UTC string
      const time = now.toISOString().substring(11, 19);
      setTimeStr(`${time} UTC`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Suppress hydration warnings since server/client time might mismatch slightly in SSR (if used)
  return (
    <div
      className={cn(
        'fixed bottom-4 left-4 z-20 pointer-events-none select-none',
        className,
      )}
      suppressHydrationWarning
    >
      <div className="bg-[#08929c] text-[#000000] px-2 py-0.5 font-mono font-bold text-[10px] tracking-wider uppercase">
        {timeStr}
      </div>
    </div>
  );
}
