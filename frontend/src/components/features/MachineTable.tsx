import { useNavigate } from "react-router-dom";
import { Thermometer } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { statusColor } from "@/utils/status";
import { formatFault, formatMaybe, timeAgo } from "@/utils/format";
import type { Machine } from "@/types";

export function MachineTable({ machines }: { machines: Machine[] }) {
  const navigate = useNavigate();
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wide text-muted">
              <th className="px-5 py-3 font-medium">Machine</th>
              <th className="px-5 py-3 font-medium">Health</th>
              <th className="px-5 py-3 font-medium">Temperature</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Prediction</th>
              <th className="px-5 py-3 font-medium">Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {machines.map((m) => (
              <tr
                key={m.id}
                onClick={() => navigate(`/machines/${m.id}`)}
                className="cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-foreground/5"
              >
                <td className="px-5 py-3">
                  <p className="font-medium text-foreground">{m.name}</p>
                  <p className="text-xs text-muted">{m.id}</p>
                </td>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-20">
                      <ProgressBar
                        value={m.health_score}
                        color={statusColor(m.status)}
                        height={6}
                      />
                    </div>
                    <span className="text-foreground tnum">
                      {m.health_score.toFixed(0)}%
                    </span>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <span className="inline-flex items-center gap-1.5 text-foreground tnum">
                    <Thermometer size={14} className="text-muted" />
                    {formatMaybe(m.temperature, 1)}°C
                  </span>
                </td>
                <td className="px-5 py-3">
                  <StatusBadge status={m.status} />
                </td>
                <td className="px-5 py-3 text-foreground">
                  {formatFault(m.predicted_fault)}
                </td>
                <td className="px-5 py-3 text-muted">
                  {timeAgo(m.last_updated)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
