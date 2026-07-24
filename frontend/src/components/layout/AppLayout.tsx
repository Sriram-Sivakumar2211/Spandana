import { useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Sidebar } from "./Sidebar";
import { Navbar } from "./Navbar";
import { Footer } from "./Footer";
import { ErrorBoundary } from "./ErrorBoundary";
import { fetchAlerts } from "@/services/spandanaService";
import type { AlertItem } from "@/types";

export function AppLayout({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [connected, setConnected] = useState(false);
  const [search, setSearch] = useState("");
  const location = useLocation();

  useEffect(() => {
    let active = true;
    const load = async () => {
      const { data, live } = await fetchAlerts();
      if (!active) return;
      setAlerts(data);
      setConnected(live);
    };
    load();
    const id = window.setInterval(load, 15000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Desktop sidebar */}
      <div className="hidden lg:block">
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((c) => !c)}
        />
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {drawerOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDrawerOpen(false)}
            />
            <motion.div
              className="absolute left-0 top-0 h-full"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 320, damping: 34 }}
            >
              <Sidebar
                collapsed={false}
                onToggleCollapse={() => {}}
                onNavigate={() => setDrawerOpen(false)}
              />
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar
          onOpenDrawer={() => setDrawerOpen(true)}
          alerts={alerts}
          connected={connected}
          search={search}
          onSearch={setSearch}
        />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">
            {/* key=pathname remounts the boundary fresh on every navigation,
                so a crash on one page doesn't keep showing the error screen
                after clicking to a different page. */}
            <ErrorBoundary key={location.pathname}>{children}</ErrorBoundary>
          </div>
          <Footer />
        </main>
      </div>
    </div>
  );
}
