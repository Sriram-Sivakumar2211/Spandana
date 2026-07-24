import { Menu, Wifi, WifiOff } from "lucide-react";
import { SearchBar } from "@/components/ui/SearchBar";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { ProfileMenu } from "@/components/ui/ProfileMenu";
import { useClock } from "@/hooks/useClock";
import type { AlertItem } from "@/types";
import { cn } from "@/utils/cn";

interface NavbarProps {
  onOpenDrawer: () => void;
  alerts: AlertItem[];
  connected: boolean;
  search: string;
  onSearch: (v: string) => void;
  showNotifications: boolean;
}

export function Navbar({
  onOpenDrawer,
  alerts,
  connected,
  search,
  onSearch,
  showNotifications,
}: NavbarProps) {
  const now = useClock();
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-md">
      <button
        onClick={onOpenDrawer}
        aria-label="Open navigation menu"
        className="grid h-10 w-10 place-items-center rounded-xl border border-border bg-card text-muted lg:hidden"
      >
        <Menu size={18} />
      </button>

      <div className="hidden max-w-sm flex-1 sm:block">
        <SearchBar value={search} onChange={onSearch} />
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
