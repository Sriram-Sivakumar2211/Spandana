import { cn } from "@/utils/cn";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg bg-foreground/5",
        className,
      )}
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-foreground/10 to-transparent" />
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-soft">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="mt-4 h-9 w-32" />
      <Skeleton className="mt-4 h-2 w-full" />
    </div>
  );
}
