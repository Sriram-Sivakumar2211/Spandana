import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { ChevronLeft, Gauge } from "lucide-react";
import { cn } from "@/utils/cn";
import { NAV_ITEMS } from "./navConfig";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  /** mobile drawer close */
  onNavigate?: () => void;
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  onNavigate,
}: SidebarProps) {
  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-border bg-sidebar transition-[width] duration-300",
        collapsed ? "w-[76px]" : "w-64",
      )}
    >
      {/* Brand */}
      <div className="flex h-16 items-center gap-3 px-4">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-soft">
          <Gauge size={20} />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate font-display text-lg leading-none text-foreground">
              SPANDANA
            </p>
            <p className="mt-1 truncate text-[11px] leading-none text-muted">
              AI Predictive Maintenance
            </p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted hover:bg-foreground/5 hover:text-foreground",
                  collapsed && "justify-center",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 -z-10 rounded-xl bg-primary/10"
                      transition={{ type: "spring", stiffness: 400, damping: 32 }}
                    />
                  )}
                  {isActive && (
                    <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-primary" />
                  )}
                  <Icon size={19} className="shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Collapse control (desktop) */}
      <div className="hidden border-t border-border p-3 lg:block">
        <button
          onClick={onToggleCollapse}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={cn(
            "flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted transition-colors hover:bg-foreground/5 hover:text-foreground",
            collapsed && "justify-center",
          )}
        >
          <ChevronLeft
            size={18}
            className={cn("transition-transform", collapsed && "rotate-180")}
          />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
