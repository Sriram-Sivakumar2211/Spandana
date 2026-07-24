import { useEffect, useState } from "react";
import type { Machine } from "@/types";
import { fetchMachines } from "@/services/spandanaService";

/** Loads the fleet once, with loading + connection state. */
export function useMachines() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      const { data, live } = await fetchMachines();
      if (!active) return;
      setMachines(data);
      setLive(live);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, []);

  return { machines, loading, live };
}
