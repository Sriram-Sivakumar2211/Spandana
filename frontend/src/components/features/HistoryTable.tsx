import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatFault, formatTime, pct } from "@/utils/format";
import type { HistoryRecord } from "@/types";

export function HistoryTable({
  rows,
  onRowClick,
}: {
  rows: HistoryRecord[];
  onRowClick: (row: HistoryRecord) => void;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wide text-muted">
              <th className="px-5 py-3 font-medium">Machine</th>
              <th className="px-5 py-3 font-medium">Date</th>
              <th className="px-5 py-3 font-medium">Prediction</th>
              <th className="px-5 py-3 font-medium">Confidence</th>
              <th className="px-5 py-3 font-medium">Health</th>
              <th className="px-5 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.id}
                onClick={() => onRowClick(r)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onRowClick(r);
                }}
                className="cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-foreground/5 focus:bg-foreground/5 focus:outline-none"
              >
                <td className="px-5 py-3">
                  <p className="font-medium text-foreground">{r.machine_name}</p>
                  <p className="text-xs text-muted">{r.machine_id}</p>
                </td>
                <td className="px-5 py-3 text-muted">{formatTime(r.timestamp)}</td>
                <td className="px-5 py-3 text-foreground">
                  {formatFault(r.predicted_fault)}
                </td>
                <td className="px-5 py-3 text-foreground tnum">
                  {pct(r.prediction_confidence, 1)}
                </td>
                <td className="px-5 py-3 text-foreground tnum">
                  {r.health_score.toFixed(1)}%
                </td>
                <td className="px-5 py-3">
                  <StatusBadge status={r.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
