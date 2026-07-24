import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import type { AlertItem } from "@/types";
import { STATUS_TOKENS } from "@/utils/status";
import { timeAgo } from "@/utils/format";

export function NotificationBell({ alerts }: { alerts: AlertItem[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const unread = alerts.filter((a) => a.severity !== "healthy").length;

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={`Notifications (${unread} active)`}
        className="relative grid h-10 w-10 place-items-center rounded-xl border border-border bg-card text-muted transition-colors hover:text-primary"
      >
        <Bell size={17} />
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-critical px-1 text-[10px] font-semibold text-white tnum">
            {unread}
          </span>
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.16 }}
            className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-2xl border border-border bg-card shadow-soft-lg"
          >
            <div className="border-b border-border px-4 py-3">
              <p className="font-display text-foreground">Notifications</p>
              <p className="text-xs text-muted">{unread} active alerts</p>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {alerts.slice(0, 6).map((a) => (
                <div
                  key={a.id}
                  className="flex gap-3 border-b border-border px-4 py-3 last:border-0"
                >
                  <span
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                    style={{ background: STATUS_TOKENS[a.severity].color }}
                  />
                  <div className="min-w-0">
                    <p className="truncate text-sm text-foreground">
                      {a.machine_name}
                    </p>
                    <p className="text-xs text-muted">{a.message}</p>
                    <p className="mt-0.5 text-[11px] text-muted">
                      {timeAgo(a.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
