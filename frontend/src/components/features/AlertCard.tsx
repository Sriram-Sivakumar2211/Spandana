import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { timeAgo } from "@/utils/format";
import { STATUS_TOKENS } from "@/utils/status";
import type { AlertItem } from "@/types";

const ICON = {
  healthy: CheckCircle2,
  warning: AlertTriangle,
  critical: ShieldAlert,
};

export function AlertCard({ alerts }: { alerts: AlertItem[] }) {
  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-display text-lg text-foreground">Recent Alerts</h3>
        <span className="rounded-full bg-foreground/5 px-2 py-0.5 text-xs text-muted">
          {alerts.length}
        </span>
      </div>
      <ul className="space-y-3">
        {alerts.slice(0, 5).map((a) => {
          const Icon = ICON[a.severity];
          const token = STATUS_TOKENS[a.severity];
          return (
            <li key={a.id} className="flex gap-3">
              <span
                className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg ${token.soft} ${token.text}`}
              >
                <Icon size={16} />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">
                  {a.machine_name}
                </p>
                <p className="text-xs text-muted">{a.message}</p>
                <p className="mt-0.5 text-[11px] text-muted">
                  {timeAgo(a.timestamp)}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
