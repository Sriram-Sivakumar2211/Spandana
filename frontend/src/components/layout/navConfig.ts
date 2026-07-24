import {
  LayoutDashboard,
  HardDrive,
  Activity,
  BrainCircuit,
  History,
  FileText,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  end?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard, end: true },
  { label: "Machines", to: "/machines", icon: HardDrive },
  { label: "Live Monitoring", to: "/monitoring", icon: Activity },
  { label: "Predictions", to: "/predictions", icon: BrainCircuit },
  { label: "History", to: "/history", icon: History },
  { label: "Reports", to: "/reports", icon: FileText },
  { label: "Settings", to: "/settings", icon: Settings },
];
