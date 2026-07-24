import { motion } from "framer-motion";
import { Card } from "@/components/ui/Card";
import { STATUS_TOKENS } from "@/utils/status";
import { formatFault, formatTime, pct } from "@/utils/format";
import type { HistoryRecord } from "@/types";

export function HistoryTimeline({
  rows,
  onRowClick,
}: {
  rows: HistoryRecord[];
  onRowClick: (row: HistoryRecord) => void;
}) {
  return (
    <Card className="p-5">
      <ol className="relative ml-3 border-l border-border">
        {rows.map((r, i) => {
          const token = STATUS_TOKENS[r.status];
          return (
            <motion.li
              key={r.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(i * 0.03, 0.5) }}
              className="mb-5 ml-5 last:mb-0"
            >
              <span
                className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full ring-4 ring-card"
                style={{ background: token.color }}
              />
              <button
                onClick={() => onRowClick(r)}
                className="w-full rounded-xl border border-border bg-background/40 p-3 text-left transition-colors hover:border-primary/40"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">
                    {r.machine_name}
                  </p>
                  <span className={`text-xs ${token.text}`}>{token.label}</span>
                </div>
                <p className="text-xs text-muted">
                  {formatFault(r.predicted_fault)} · {pct(r.prediction_confidence, 0)} confidence
                </p>
                <p className="mt-0.5 text-[11px] text-muted">
                  {formatTime(r.timestamp)}
                </p>
              </button>
            </motion.li>
          );
        })}
      </ol>
    </Card>
  );
}
