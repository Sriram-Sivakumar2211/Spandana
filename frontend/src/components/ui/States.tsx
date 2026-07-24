import type { ReactNode } from "react";
import { Inbox, TriangleAlert } from "lucide-react";
import { Button } from "./Button";

export function EmptyState({
  title = "Nothing here yet",
  message,
  icon,
}: {
  title?: string;
  message?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 px-6 py-14 text-center">
      <div className="mb-3 grid h-12 w-12 place-items-center rounded-full bg-foreground/5 text-muted">
        {icon ?? <Inbox size={22} />}
      </div>
      <p className="text-lg text-foreground">{title}</p>
      {message && <p className="mt-1 max-w-sm text-sm text-muted">{message}</p>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-critical/30 bg-critical/5 px-6 py-14 text-center">
      <div className="mb-3 grid h-12 w-12 place-items-center rounded-full bg-critical/10 text-critical">
        <TriangleAlert size={22} />
      </div>
      <p className="text-lg text-foreground">{title}</p>
      {message && <p className="mt-1 max-w-sm text-sm text-muted">{message}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
