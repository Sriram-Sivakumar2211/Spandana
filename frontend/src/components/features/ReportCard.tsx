import {
  ClipboardList,
  Download,
  FileText,
  Gauge,
  Printer,
  ShieldAlert,
  Wrench,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { HealthGauge } from "./HealthGauge";
import { formatSource, formatTime, pct } from "@/utils/format";
import type { Machine, MaintenanceReport } from "@/types";

const SEVERITY_STYLE: Record<MaintenanceReport["severity"], string> = {
  healthy: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  critical: "bg-critical/10 text-critical",
};

/**
 * Renders the REAL RAG + LLM maintenance report shape (severity/title/summary/
 * evidence/likely_cause/recommended_action[]/urgency/confidence/notes --
 * matches backend/schema/maintenance_report.json exactly). `machine` supplies
 * display-only context (name/location/source/health_score) the report itself
 * doesn't carry.
 */
export function ReportCard({
  report,
  machine,
  onDownload,
}: {
  report: MaintenanceReport;
  machine?: Machine;
  onDownload: () => void;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border bg-primary/5 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground">
            <FileText size={19} />
          </span>
          <div>
            <h3 className="font-display text-lg text-foreground">
              AI Maintenance Report
            </h3>
            <p className="text-xs text-muted">
              {machine?.name ?? report.machine_id} · Generated {formatTime(report.timestamp)}
            </p>
          </div>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${SEVERITY_STYLE[report.severity]}`}>
          {report.urgency}
        </span>
      </div>

      <div className="grid gap-6 p-5 lg:grid-cols-[240px_1fr]">
        {/* Left: identity + gauge */}
        <div className="space-y-4">
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-background/50 p-4">
            <HealthGauge score={machine?.health_score ?? (1 - report.confidence) * 100} />
            <StatusBadge status={report.severity} />
          </div>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">Machine ID</dt>
              <dd className="text-foreground">{report.machine_id}</dd>
            </div>
            {machine?.source && (
              <div className="flex justify-between">
                <dt className="text-muted">Source</dt>
                <dd className="text-foreground">{formatSource(machine.source)}</dd>
              </div>
            )}
            {machine?.location && (
              <div className="flex justify-between">
                <dt className="text-muted">Location</dt>
                <dd className="text-right text-foreground">{machine.location}</dd>
              </div>
            )}
            <div className="flex justify-between">
              <dt className="text-muted">Confidence</dt>
              <dd className="text-foreground tnum">{pct(report.confidence, 1)}</dd>
            </div>
          </dl>
        </div>

        {/* Right: narrative */}
        <div className="space-y-5">
          <div>
            <div className="mb-2 flex items-center gap-2 text-foreground">
              <Gauge size={16} className="text-primary" />
              <h4 className="font-display text-base">{report.title}</h4>
            </div>
            <p className="text-sm text-muted">{report.summary}</p>
          </div>

          <section>
            <div className="mb-2 flex items-center gap-2 text-foreground">
              <ClipboardList size={16} className="text-primary" />
              <h4 className="font-display text-base">Diagnostic Evidence</h4>
            </div>
            <ul className="space-y-1.5">
              {report.evidence.map((e, i) => (
                <li
                  key={i}
                  className="flex gap-2 text-sm text-muted before:mt-2 before:h-1 before:w-1 before:shrink-0 before:rounded-full before:bg-primary"
                >
                  {e}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <div className="mb-2 flex items-center gap-2 text-foreground">
              <ShieldAlert size={16} className="text-primary" />
              <h4 className="font-display text-base">Likely Cause</h4>
            </div>
            <p className="text-sm text-foreground">{report.likely_cause}</p>
          </section>

          <section>
            <div className="mb-2 flex items-center gap-2 text-foreground">
              <Wrench size={16} className="text-primary" />
              <h4 className="font-display text-base">Recommended Actions</h4>
            </div>
            <ol className="space-y-2">
              {report.recommended_action.map((a, i) => (
                <li key={i} className="flex gap-3 text-sm text-foreground">
                  <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-primary/15 text-[11px] font-semibold text-primary tnum">
                    {i + 1}
                  </span>
                  {a}
                </li>
              ))}
            </ol>
          </section>

          {report.notes && (
            <div className="flex items-start gap-2 rounded-xl border border-warning/30 bg-warning/5 p-3">
              <ShieldAlert size={16} className="mt-0.5 shrink-0 text-warning" />
              <p className="text-sm text-foreground">{report.notes}</p>
            </div>
          )}

          <div className="flex flex-wrap gap-2 border-t border-border pt-4">
            <Button onClick={onDownload}>
              <Download size={16} /> Download Report
            </Button>
            <Button variant="secondary" onClick={() => window.print()}>
              <Printer size={16} /> Print
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
