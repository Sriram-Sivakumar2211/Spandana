import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

interface Crumb {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: Crumb[];
  actions?: ReactNode;
}

export function PageHeader({
  title,
  subtitle,
  breadcrumbs,
  actions,
}: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav
            aria-label="Breadcrumb"
            className="mb-1.5 flex items-center gap-1 text-xs text-muted"
          >
            {breadcrumbs.map((c, i) => (
              <span key={i} className="flex items-center gap-1">
                {c.to ? (
                  <Link
                    to={c.to}
                    className="transition-colors hover:text-primary"
                  >
                    {c.label}
                  </Link>
                ) : (
                  <span className="text-foreground">{c.label}</span>
                )}
                {i < breadcrumbs.length - 1 && <ChevronRight size={12} />}
              </span>
            ))}
          </nav>
        )}
        <h1 className="text-2xl text-foreground sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
