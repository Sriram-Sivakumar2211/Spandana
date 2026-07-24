import { useEffect, useRef, useState } from "react";
import { LogOut, Settings, User } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Link } from "react-router-dom";

export function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

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
        aria-label="Profile menu"
        className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-sm font-semibold text-primary-foreground shadow-soft transition-transform hover:scale-105"
      >
        SM
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.16 }}
            className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-2xl border border-border bg-card shadow-soft-lg"
          >
            <div className="border-b border-border px-4 py-3">
              <p className="text-sm text-foreground">Site Maintenance</p>
              <p className="text-xs text-muted">reliability@spandana.io</p>
            </div>
            <div className="p-1.5">
              <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-foreground/5 hover:text-foreground">
                <User size={15} /> Profile
              </button>
              <Link
                to="/settings"
                onClick={() => setOpen(false)}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-foreground/5 hover:text-foreground"
              >
                <Settings size={15} /> Settings
              </Link>
              <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-critical transition-colors hover:bg-critical/10">
                <LogOut size={15} /> Sign out
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
