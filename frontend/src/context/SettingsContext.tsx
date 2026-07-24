import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

/*
  App-wide user preferences that actually drive behavior (not decorative):
    - replaySpeed        : multiplier consumed by Live Monitoring to set its
                           real polling interval (higher = faster streaming).
    - notificationsEnabled: gates whether the app polls the real /alerts
                           endpoint and shows the notification bell badge.
  Both are persisted to localStorage so they survive reloads, and both are
  read by real components -- see LiveMonitoring and AppLayout/NotificationBell.
*/

interface SettingsValue {
  replaySpeed: number;
  setReplaySpeed: (v: number) => void;
  notificationsEnabled: boolean;
  setNotificationsEnabled: (v: boolean) => void;
}

const SettingsContext = createContext<SettingsValue | undefined>(undefined);

const KEY_SPEED = "spandana-replay-speed";
const KEY_NOTIF = "spandana-notifications";

function readNumber(key: string, fallback: number): number {
  if (typeof window === "undefined") return fallback;
  const v = Number(window.localStorage.getItem(key));
  return Number.isFinite(v) && v > 0 ? v : fallback;
}

function readBool(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const v = window.localStorage.getItem(key);
  return v === null ? fallback : v === "true";
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [replaySpeed, setReplaySpeedState] = useState(() => readNumber(KEY_SPEED, 1));
  const [notificationsEnabled, setNotifState] = useState(() => readBool(KEY_NOTIF, true));

  useEffect(() => {
    window.localStorage.setItem(KEY_SPEED, String(replaySpeed));
  }, [replaySpeed]);
  useEffect(() => {
    window.localStorage.setItem(KEY_NOTIF, String(notificationsEnabled));
  }, [notificationsEnabled]);

  const setReplaySpeed = useCallback((v: number) => setReplaySpeedState(v), []);
  const setNotificationsEnabled = useCallback((v: boolean) => setNotifState(v), []);

  const value = useMemo(
    () => ({ replaySpeed, setReplaySpeed, notificationsEnabled, setNotificationsEnabled }),
    [replaySpeed, setReplaySpeed, notificationsEnabled, setNotificationsEnabled],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used within a SettingsProvider");
  return ctx;
}
