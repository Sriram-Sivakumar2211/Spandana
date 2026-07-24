import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { CounterStat } from "@/components/ui/CounterStat";
import { cn } from "@/utils/cn";

interface HealthCardProps {
  label: string;
  value: number;
  suffix?: string;
  decimals?: number;
  icon: LucideIcon;
  tone?: "primary" | "success" | "warning" | "critical" | "muted";
  hint?: string;
  index?: number;
}

const TONE: Record<string, { text: string; soft: string }> = {
  primary: { text: "text-primary", soft: "bg-primary/10" },
  success: { text: "text-success", soft: "bg-success/10" },
  warning: { text: "text-warning", soft: "bg-warning/10" },
  critical: { text: "text-critical", soft: "bg-critical/10" },
  muted: { text: "text-muted", soft: "bg-foreground/5" },
};

export function HealthCard({
  label,
  value,
  suffix = "",
  decimals = 0,
  icon: Icon,
  tone = "primary",
  hint,
  index = 0,
}: HealthCardProps) {
  const t = TONE[tone];
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.4 }}
    >
      <Card className="p-5 transition-shadow hover:shadow-soft-lg">
        <div className="flex items-start justify-between">
          <p className="text-sm text-muted">{label}</p>
          <span className={cn("grid h-9 w-9 place-items-center rounded-xl", t.soft, t.text)}>
            <Icon size={18} />
          </span>
        </div>
        <p className="mt-3 text-3xl text-foreground tnum">
          <CounterStat value={value} decimals={decimals} suffix={suffix} />
        </p>
        {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
      </Card>
    </motion.div>
  );
}
