import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Menu, Wifi, WifiOff } from "lucide-react";
import { SearchBar } from "@/components/ui/SearchBar";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { ProfileMenu } from "@/components/ui/ProfileMenu";
import { useClock } from "@/hooks/useClock";
import { STATUS_TOKENS } from "@/utils/status";
import { formatSource } from "@/utils/format";
import type { AlertItem, Machine } from "@/types";
import { cn } from "@/utils/cn";

interface NavbarProps {
  onOpenDrawer: () => void;
  alerts: AlertItem[];
  connected: boolean;
  search: string;
  onSearch: (v: string) => void;
  showNotifications: boolean;
  machines: Machine[];
}

export function Navbar({
  onOpenDrawer,
  alerts,
  connected,
  search,
  onSearch,
  showNotifications,
  machines,
}: NavbarProps) {
  const now = useClock();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const matches = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [];
    return machines
      .filter(
        (m) =>
          m.name.toLowerCase().includes(q) ||
          m.id.toLowerCase().includes(q) ||
          (m.source ? formatSource(m.source).toLowerCase().includes(q) : false),
      )
      .slice(0, 6);
  }, [machines, search]);

  const goToMachine = (id: string) => {
    setOpen(false);
    onSearch("");
    navigate(`/machines/${id}`);
  };

  const submitSearch = () => {
    if (!search.trim()) return;
    setOpen(false);
    navigate(`/machines?q=${encodeURIComponent(search.trim())}`);
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-md">
      <button
        onClick={onOpenDrawer}
        aria-label="Open navigation menu"
        className="grid h-10 w-10 place-items-center rounded-xl border border-border bg-card text-muted lg:hidden"
      >
        <Menu size={18} />
      </button>

      <div className="relative hidden max-w-sm flex-1 sm:block">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitSearch();
          }}
        >
          <SearchBar
            value={search}
            onChange={(v) => {
              onSearch(v);
              setOpen(v.trim().length > 0);
            }}
            onFocus={() => setOpen(search.trim().length > 0)}
            onBlur={() => setOpen(false)}
          />
        </form>

        {open && search.trim() && (
          <div
            className="absolute left-0 right-0 top-full z-40 mt-2 overflow-hidden rounded-xl border border-border bg-card shadow-soft-lg"
            onMouseDown={(e) => e.preventDefault()}
          >
            {matches.length === 0 ? (
              <p className="px-4 py-3 text-sm text-muted">
                No machines match "{search.trim()}".
              </p>
            ) : (
              <ul>
                {matches.map((m) => (
                  <li key={m.id}>
                    <button
                      type="button"
                      onClick={() => goToMachine(m.id)}
                      className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm transition-colors hover:bg-foreground/5"
                    >
                      <span
                        className="h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{ background: STATUS_TOKENS[m.status].color }}
                      />
                      <span className="min-w-0 flex-1 truncate text-foreground">
                        {m.name}
                      </span>
                      <span className="shrink-0 text-xs text-muted">
                        {m.id}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <button
              type="button"
              onClick={submitSearch}
              className="block w-full border-t border-border px-4 py-2 text-left text-xs text-primary hover:bg-foreground/5"
            >
              See all results for "{search.trim()}"
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-1 items-center justify-end gap-2 sm:gap-3">
        {/* Connection status */}
        <div
          className={cn(
            "hidden items-center gap-1.5 rounded-xl border border-border bg-card px-3 py-2 text-xs md:flex",
            connected ? "text-success" : "text-warning",
          )}
          title={connected ? "Backend connected" : "Backend offline — showing demo data"}
        >
          {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
          <span className="font-medium">
            {connected ? "Live" : "Demo Mode"}
          </span>
        </div>

        {/* Clock */}
        <div className="hidden flex-col items-end lg:flex">
          <span className="text-sm text-foreground tnum">
            {now.toLocaleTimeString(undefined, {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>
          <span className="text-[11px] text-muted">
            {now.toLocaleDateString(undefined, {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </span>
        </div>

        <ThemeToggle />
        {showNotifications && <NotificationBell alerts={alerts} />}
        <ProfileMenu />
      </div>
    </header>
  );
}
