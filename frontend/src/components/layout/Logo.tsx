import { cn } from "@/utils/cn";

/*
  Spandana brand mark, recreated as a themeable inline SVG. It draws in
  `currentColor`, so it inherits the surrounding text color: dark navy on a
  light background, inverting to near-white in dark mode -- the flip is
  automatic, no second asset. Four rounded bars woven in 4-fold rotational
  symmetry read as the interlocking "knot" motif.

  To use your exact logo art instead: drop the PNG at
  frontend/public/spandana-logo.png and replace <LogoMark/> with an <img>.
*/
export function LogoMark({
  size = 28,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      role="img"
      aria-label="Spandana logo"
      className={className}
    >
      {[0, 90, 180, 270].map((deg) => (
        <rect
          key={deg}
          x="30"
          y="39"
          width="46"
          height="14"
          rx="7"
          fill="currentColor"
          transform={`rotate(${deg} 50 50)`}
        />
      ))}
      {/* center knockout to read as a woven knot rather than a solid blob */}
      <rect x="42" y="42" width="16" height="16" rx="4" className="fill-sidebar" />
    </svg>
  );
}

export function Logo({
  collapsed = false,
  className,
  markSize = 34,
}: {
  collapsed?: boolean;
  className?: string;
  markSize?: number;
}) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <LogoMark size={markSize} className="text-foreground transition-colors" />
      {!collapsed && (
        <div className="min-w-0 leading-none">
          <p className="truncate text-xl font-semibold tracking-tight text-foreground">
            Spandana
          </p>
          <p className="mt-1 truncate text-[10.5px] font-medium uppercase tracking-[0.18em] text-muted">
            Predictive Maintenance
          </p>
        </div>
      )}
    </div>
  );
}
