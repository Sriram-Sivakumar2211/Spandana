import { Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { AppLayout } from "@/components/layout/AppLayout";
import Dashboard from "@/pages/Dashboard";
import Machines from "@/pages/Machines";
import MachineDetail from "@/pages/MachineDetail";
import LiveMonitoring from "@/pages/LiveMonitoring";
import Predictions from "@/pages/Predictions";
import History from "@/pages/History";
import Reports from "@/pages/Reports";
import Settings from "@/pages/Settings";
import NotFound from "@/pages/NotFound";

export default function App() {
  const location = useLocation();
  return (
    <AppLayout>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/machines" element={<Machines />} />
          <Route path="/machines/:id" element={<MachineDetail />} />
          <Route path="/monitoring" element={<LiveMonitoring />} />
          <Route path="/predictions" element={<Predictions />} />
          <Route path="/history" element={<History />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AnimatePresence>
    </AppLayout>
  );
}
