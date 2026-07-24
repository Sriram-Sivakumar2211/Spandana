import { useState } from "react";
import { Check, Globe, Info, Server, SlidersHorizontal } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useTheme } from "@/hooks/useTheme";
import { getApiBase, setApiBase } from "@/services/api";
import { cn } from "@/utils/cn";

function Section({
  icon: Icon,
  title,
  desc,
  children,
}: {
  icon: typeof Server;
  title: string;
  desc: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-5">
      <div className="mb-4 flex items-start gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/10 text-primary">
          <Icon size={17} />
        </span>
        <div>
          <h3 className="font-display text-lg text-foreground">{title}</h3>
          <p className="text-sm text-muted">{desc}</p>
        </div>
      </div>
      {children}
    </Card>
  );
}

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const [apiBase, setApiBaseInput] = useState(getApiBase());
  const [replaySpeed, setReplaySpeed] = useState(1);
  const [notifications, setNotifications] = useState(true);
  const [language, setLanguage] = useState("en");
  const [saved, setSaved] = useState(false);

  const save = () => {
    setApiBase(apiBase);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  };

  return (
    <PageTransition>
      <PageHeader
        title="Settings"
        subtitle="Configure appearance, streaming and backend connection."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Settings" }]}
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Section
          icon={SlidersHorizontal}
          title="Appearance"
          desc="Choose how SPANDANA looks. Saved to your browser."
        >
          <div className="flex gap-2">
            {(["light", "dark"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTheme(t)}
                className={cn(
                  "flex-1 rounded-xl border px-4 py-3 text-sm capitalize transition-colors",
                  theme === t
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted hover:text-foreground",
                )}
              >
                {t} Mode
              </button>
            ))}
          </div>
        </Section>

        <Section
          icon={Server}
          title="Backend Connection"
          desc="API base URL used for /predict, /history, /report, /stream."
        >
          <label className="mb-1.5 block text-xs text-muted">API Base URL</label>
          <input
            value={apiBase}
            onChange={(e) => setApiBaseInput(e.target.value)}
            className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm text-foreground focus:border-primary focus:outline-none"
            placeholder="http://localhost:8000"
          />
          <Button size="sm" className="mt-3" onClick={save}>
            {saved ? <Check size={15} /> : null}
            {saved ? "Saved" : "Save"}
          </Button>
        </Section>

        <Section
          icon={SlidersHorizontal}
          title="Replay Speed"
          desc="Stream simulation speed multiplier for Live Monitoring."
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              min={0.5}
              max={4}
              step={0.5}
              value={replaySpeed}
              onChange={(e) => setReplaySpeed(Number(e.target.value))}
              className="flex-1 accent-[var(--primary)]"
              aria-label="Replay speed"
            />
            <span className="w-12 text-right text-sm text-foreground tnum">
              {replaySpeed.toFixed(1)}×
            </span>
          </div>
        </Section>

        <Section
          icon={Globe}
          title="Preferences"
          desc="Notifications and language."
        >
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <span className="text-sm text-foreground">Enable notifications</span>
              <button
                onClick={() => setNotifications((n) => !n)}
                role="switch"
                aria-checked={notifications}
                aria-label="Toggle notifications"
                className={cn(
                  "relative h-6 w-11 rounded-full transition-colors",
                  notifications ? "bg-primary" : "bg-foreground/20",
                )}
              >
                <span
                  className={cn(
                    "absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform",
                    notifications ? "translate-x-5" : "translate-x-0.5",
                  )}
                />
              </button>
            </label>
            <div>
              <label className="mb-1.5 block text-xs text-muted">Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm text-foreground focus:border-primary focus:outline-none"
              >
                <option value="en">English</option>
                <option value="hi">हिन्दी (Hindi)</option>
                <option value="ta">தமிழ் (Tamil)</option>
                <option value="de">Deutsch</option>
              </select>
            </div>
          </div>
        </Section>
      </div>

      <Card className="mt-5 p-5">
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/10 text-primary">
            <Info size={17} />
          </span>
          <div>
            <h3 className="font-display text-lg text-foreground">About SPANDANA</h3>
            <p className="mt-1 max-w-2xl text-sm text-muted">
              SPANDANA is an AI-powered predictive maintenance platform for
              industrial machines. Its production model is a Liquid Time-Constant
              Network (LTC) built on the official MIT{" "}
              <span className="text-foreground">ncps</span> library, serving
              stateful, continuous-time fault predictions across bearing and
              motor telemetry.
            </p>
            <p className="mt-2 text-xs text-muted">Version 1.0.0 · Hackathon MVP</p>
          </div>
        </div>
      </Card>
    </PageTransition>
  );
}
