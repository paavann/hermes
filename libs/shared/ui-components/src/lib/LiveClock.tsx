import { useState, useEffect } from 'react';

export function LiveClock() {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      // Format: HH:MM:SS from UTC string
      const time = now.toISOString().substring(11, 19);
      setTimeStr(`SYS.TIME ${time} UTC`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Suppress hydration warnings since server/client time might mismatch slightly in SSR (if used)
  return (
    <div className="fixed bottom-4 left-4 z-20 pointer-events-none" suppressHydrationWarning>
      <div className="bg-hud-bg border border-hud-border px-3 py-1.5 font-mono text-xs text-neon-blue tracking-[0.1em] shadow-[0_0_10px_rgba(59,130,246,0.2)] backdrop-blur-md">
        {timeStr}
      </div>
    </div>
  );
}
