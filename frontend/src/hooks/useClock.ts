import { useEffect, useState } from "react";

/** Ticking wall-clock for the navbar (updates once per second). */
export function useClock() {
  const [now, setNow] = useState<Date>(new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return now;
}
