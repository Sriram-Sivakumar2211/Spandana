import { Search } from "lucide-react";
import { cn } from "@/utils/cn";

interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchBar({
  value,
  onChange,
  placeholder = "Search machines…",
  className,
}: SearchBarProps) {
  return (
    <div className={cn("relative", className)}>
      <Search
        size={16}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="h-10 w-full rounded-xl border border-border bg-background pl-9 pr-3 text-sm text-foreground placeholder:text-muted focus:border-primary focus:outline-none"
      />
    </div>
  );
}
